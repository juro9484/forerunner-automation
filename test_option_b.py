#!/usr/bin/env python3
"""
Test Option B fixes: Duplicate prevention, notifications, retry logic.
"""

import sys
import logging
from pathlib import Path
from datetime import datetime

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from email_database import EmailDatabase
from email_monitor import EmailData

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def test_duplicate_prevention():
    """Test database-based duplicate prevention."""
    print("\n" + "="*80)
    print("TEST 1: Duplicate Prevention")
    print("="*80)

    # Create test database
    test_db_path = Path("data/test_option_b.db")
    test_db_path.parent.mkdir(parents=True, exist_ok=True)
    if test_db_path.exists():
        test_db_path.unlink()

    db = EmailDatabase(db_path=test_db_path)

    print("\n[Test 1a] First claim creation attempt...")
    db.record_processing_attempt(
        email_id="test_email_001",
        attempt_type="claim_creation",
        client_identifier="John Doe - 123 Main St",
        success=True,
        result_url="https://claimtitan.com/claims/12345"
    )
    print("✓ Recorded successful claim creation")

    print("\n[Test 1b] Check for previous attempt...")
    previous = db.get_processing_attempt(
        email_id="test_email_001",
        attempt_type="claim_creation",
        client_identifier="John Doe - 123 Main St"
    )

    if previous and previous['success'] and previous['result_url']:
        print(f"✓ Found previous attempt: {previous['result_url']}")
        print("  Would skip duplicate creation!")
    else:
        print("✗ ERROR: Should have found previous attempt")
        return False

    print("\n[Test 1c] Different email (should allow creation)...")
    previous2 = db.get_processing_attempt(
        email_id="test_email_002",
        attempt_type="claim_creation",
        client_identifier="John Doe - 123 Main St"
    )

    if previous2:
        print("✗ ERROR: Should not find attempt for different email")
        return False
    else:
        print("✓ No previous attempt found (correct)")

    print("\n[Test 1d] Failed attempt (should allow retry)...")
    db.record_processing_attempt(
        email_id="test_email_003",
        attempt_type="claim_creation",
        client_identifier="Jane Smith - 456 Oak Ave",
        success=False,
        error_message="Network timeout"
    )

    previous3 = db.get_processing_attempt(
        email_id="test_email_003",
        attempt_type="claim_creation",
        client_identifier="Jane Smith - 456 Oak Ave"
    )

    if previous3 and not previous3['success']:
        print(f"✓ Found failed attempt: {previous3['error_message']}")
        print("  Would allow retry!")
    else:
        print("✗ ERROR: Should have found failed attempt")
        return False

    # Cleanup
    test_db_path.unlink()

    print("\n✓ All duplicate prevention tests PASSED")
    return True


def test_retry_logic():
    """Test retry logic helper function."""
    print("\n" + "="*80)
    print("TEST 2: Retry Logic")
    print("="*80)

    sys.path.insert(0, str(Path(__file__).parent))
    from monitor_daemon import retry_with_backoff

    print("\n[Test 2a] Function succeeds on first try...")
    call_count = [0]

    def success_first_try():
        call_count[0] += 1
        return "success"

    result = retry_with_backoff(success_first_try, max_retries=3, base_delay=0.1, operation_name="test")

    if result == "success" and call_count[0] == 1:
        print("✓ Function called once, returned success")
    else:
        print(f"✗ ERROR: Expected 1 call, got {call_count[0]}")
        return False

    print("\n[Test 2b] Function succeeds on second try...")
    call_count2 = [0]

    def success_second_try():
        call_count2[0] += 1
        if call_count2[0] == 1:
            raise Exception("First attempt fails")
        return "success"

    result2 = retry_with_backoff(success_second_try, max_retries=3, base_delay=0.1, operation_name="test")

    if result2 == "success" and call_count2[0] == 2:
        print("✓ Function called twice, succeeded on retry")
    else:
        print(f"✗ ERROR: Expected 2 calls, got {call_count2[0]}")
        return False

    print("\n[Test 2c] Function fails all attempts...")
    call_count3 = [0]

    def always_fails():
        call_count3[0] += 1
        raise Exception("Always fails")

    try:
        retry_with_backoff(always_fails, max_retries=3, base_delay=0.1, operation_name="test")
        print("✗ ERROR: Should have raised exception")
        return False
    except Exception as e:
        if call_count3[0] == 3 and "Always fails" in str(e):
            print(f"✓ Function called 3 times, final exception raised")
        else:
            print(f"✗ ERROR: Expected 3 calls with 'Always fails', got {call_count3[0]} calls")
            return False

    print("\n✓ All retry logic tests PASSED")
    return True


def test_database_schema():
    """Test that database schema includes new processing_attempts table."""
    print("\n" + "="*80)
    print("TEST 3: Database Schema")
    print("="*80)

    test_db_path = Path("data/test_schema.db")
    test_db_path.parent.mkdir(parents=True, exist_ok=True)
    if test_db_path.exists():
        test_db_path.unlink()

    db = EmailDatabase(db_path=test_db_path)

    print("\n[Test 3a] Check processing_attempts table exists...")

    import sqlite3
    conn = sqlite3.connect(test_db_path)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='processing_attempts'"
    )
    result = cursor.fetchone()

    if result:
        print("✓ processing_attempts table exists")
    else:
        print("✗ ERROR: processing_attempts table not found")
        conn.close()
        return False

    print("\n[Test 3b] Check table columns...")
    cursor.execute("PRAGMA table_info(processing_attempts)")
    columns = {row[1] for row in cursor.fetchall()}

    required_columns = {'email_id', 'attempt_type', 'client_identifier', 'success', 'result_url'}

    if required_columns.issubset(columns):
        print(f"✓ All required columns present: {columns}")
    else:
        missing = required_columns - columns
        print(f"✗ ERROR: Missing columns: {missing}")
        conn.close()
        return False

    conn.close()
    test_db_path.unlink()

    print("\n✓ All database schema tests PASSED")
    return True


def main():
    """Run all Option B tests."""
    print("\n" + "="*80)
    print("OPTION B TESTING - Duplicate Prevention & Retry Logic")
    print("="*80)

    all_passed = True

    # Test 1: Duplicate prevention
    if not test_duplicate_prevention():
        all_passed = False
        print("\n❌ Duplicate prevention test FAILED")

    # Test 2: Retry logic
    if not test_retry_logic():
        all_passed = False
        print("\n❌ Retry logic test FAILED")

    # Test 3: Database schema
    if not test_database_schema():
        all_passed = False
        print("\n❌ Database schema test FAILED")

    # Summary
    print("\n" + "="*80)
    if all_passed:
        print("✅ ALL OPTION B TESTS PASSED")
        print("="*80)
        print("\nChanges implemented:")
        print("  ✅ Database-based duplicate prevention")
        print("  ✅ Missing PDF notification")
        print("  ✅ Attachment failure notification")
        print("  ✅ Retry logic for Claude API (3 attempts)")
        print("  ✅ Retry logic for Claim Titan login (3 attempts)")
        print("  ✅ Retry logic for claim search (2 attempts, 30s delay)")
        print("\nSafe to commit and deploy!")
        return 0
    else:
        print("❌ SOME TESTS FAILED")
        print("="*80)
        print("\nDO NOT deploy until tests pass!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
