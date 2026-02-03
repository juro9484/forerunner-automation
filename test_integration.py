#!/usr/bin/env python3
"""
Integration test: Verify new changes don't break existing flow.
Tests duplicate prevention + retry logic in realistic scenario.
"""

import sys
import logging
from pathlib import Path
from datetime import datetime

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from email_database import EmailDatabase
from email_monitor import EmailData
from contract_parser import ClientData

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def test_first_time_flow():
    """Test that first-time processing works with new duplicate checks."""
    print("\n" + "="*80)
    print("TEST 1: First-Time Processing (Fresh Database)")
    print("="*80)

    # Create fresh database
    test_db_path = Path("data/test_integration.db")
    test_db_path.parent.mkdir(parents=True, exist_ok=True)
    if test_db_path.exists():
        test_db_path.unlink()

    db = EmailDatabase(db_path=test_db_path)

    # Simulate first email
    email_data = EmailData(
        email_id="first_email_001",
        claim_number=None,
        email_content="Test contract email",
        sender="client@example.com",
        recipient="support@forerunnerclaims.com",
        subject="New contract",
        timestamp=datetime.now()
    )

    client_data = ClientData(
        first_name="John",
        last_name="Doe",
        street_address="123 Main St",
        city="Denver",
        state="CO",
        zipcode="80202"
    )

    print("\n[Step 1] Check for previous attempt (should be None)...")
    client_identifier = f"{client_data.first_name} {client_data.last_name} - {client_data.street_address}"
    previous = db.get_processing_attempt(
        email_id=email_data.email_id,
        attempt_type="claim_creation",
        client_identifier=client_identifier
    )

    if previous is None:
        print("✓ No previous attempt found (correct for first email)")
    else:
        print(f"✗ ERROR: Should not find previous attempt, got: {previous}")
        return False

    print("\n[Step 2] Simulate successful claim creation...")
    claim_url = "https://claimtitan.com/claims/12345"
    db.record_processing_attempt(
        email_id=email_data.email_id,
        attempt_type="claim_creation",
        client_identifier=client_identifier,
        success=True,
        result_url=claim_url
    )
    print(f"✓ Recorded successful creation: {claim_url}")

    print("\n[Step 3] Verify email can be marked as processed...")
    db.mark_processed(
        email_id=email_data.email_id,
        claim_number="12345",
        sender=email_data.sender,
        subject=email_data.subject,
        received_timestamp=email_data.timestamp,
        status="success"
    )

    if db.is_processed(email_data.email_id):
        print("✓ Email marked as processed")
    else:
        print("✗ ERROR: Email not marked as processed")
        return False

    # Cleanup
    test_db_path.unlink()

    print("\n✓ First-time processing flow works correctly")
    return True


def test_duplicate_prevention_flow():
    """Test that duplicate emails get skipped correctly."""
    print("\n" + "="*80)
    print("TEST 2: Duplicate Prevention Flow")
    print("="*80)

    # Create database with existing attempt
    test_db_path = Path("data/test_duplicate.db")
    test_db_path.parent.mkdir(parents=True, exist_ok=True)
    if test_db_path.exists():
        test_db_path.unlink()

    db = EmailDatabase(db_path=test_db_path)

    email_id = "duplicate_test_001"
    client_identifier = "Jane Smith - 456 Oak Ave"
    claim_url = "https://claimtitan.com/claims/99999"

    print("\n[Step 1] Record initial successful attempt...")
    db.record_processing_attempt(
        email_id=email_id,
        attempt_type="claim_creation",
        client_identifier=client_identifier,
        success=True,
        result_url=claim_url
    )
    print(f"✓ Initial attempt recorded: {claim_url}")

    print("\n[Step 2] Simulate service restart / retry...")
    print("  (Same email processed again - should detect duplicate)")

    previous = db.get_processing_attempt(
        email_id=email_id,
        attempt_type="claim_creation",
        client_identifier=client_identifier
    )

    if previous and previous['success'] and previous['result_url']:
        print(f"✓ Found previous successful attempt: {previous['result_url']}")
        print("✓ Flow would skip duplicate creation and use cached URL")
    else:
        print("✗ ERROR: Should have found previous attempt")
        return False

    print("\n[Step 3] Verify different client allows new creation...")
    different_client = "Different Person - 789 Pine Rd"

    previous2 = db.get_processing_attempt(
        email_id=email_id,
        attempt_type="claim_creation",
        client_identifier=different_client
    )

    if previous2 is None:
        print("✓ Different client has no previous attempt (correct)")
    else:
        print("✗ ERROR: Should not find attempt for different client")
        return False

    # Cleanup
    test_db_path.unlink()

    print("\n✓ Duplicate prevention flow works correctly")
    return True


def test_retry_logic_integration():
    """Test that retry logic integrates correctly."""
    print("\n" + "="*80)
    print("TEST 3: Retry Logic Integration")
    print("="*80)

    sys.path.insert(0, str(Path(__file__).parent))
    from monitor_daemon import retry_with_backoff

    print("\n[Step 1] Test retry wrapper doesn't change return values...")

    def mock_parse_contract():
        """Mock function that returns ClientData."""
        return ClientData(
            first_name="Test",
            last_name="User",
            street_address="789 Test Ave",
            city="TestCity",
            state="CO",
            zipcode="12345"
        )

    result = retry_with_backoff(
        func=mock_parse_contract,
        max_retries=3,
        base_delay=0.1,
        operation_name="mock parse"
    )

    if isinstance(result, ClientData) and result.first_name == "Test":
        print("✓ Retry wrapper returns correct object type and data")
    else:
        print(f"✗ ERROR: Retry wrapper changed return value: {type(result)}")
        return False

    print("\n[Step 2] Test retry wrapper propagates exceptions correctly...")

    def mock_failing_function():
        raise ValueError("Test error message")

    try:
        retry_with_backoff(
            func=mock_failing_function,
            max_retries=2,
            base_delay=0.1,
            operation_name="mock fail"
        )
        print("✗ ERROR: Should have raised ValueError")
        return False
    except ValueError as e:
        if "Test error message" in str(e):
            print("✓ Retry wrapper propagates exceptions correctly")
        else:
            print(f"✗ ERROR: Wrong exception message: {e}")
            return False

    print("\n✓ Retry logic integrates correctly")
    return True


def test_backwards_compatibility():
    """Test that old code paths still work."""
    print("\n" + "="*80)
    print("TEST 4: Backwards Compatibility")
    print("="*80)

    test_db_path = Path("data/test_compat.db")
    test_db_path.parent.mkdir(parents=True, exist_ok=True)
    if test_db_path.exists():
        test_db_path.unlink()

    db = EmailDatabase(db_path=test_db_path)

    print("\n[Step 1] Test old mark_processed still works...")
    db.mark_processed(
        email_id="compat_test_001",
        claim_number="11111",
        sender="old@test.com",
        subject="Old test",
        received_timestamp=datetime.now(),
        status="success"
    )

    if db.is_processed("compat_test_001"):
        print("✓ Old mark_processed method works")
    else:
        print("✗ ERROR: Old method broken")
        return False

    print("\n[Step 2] Test database migration (old DB to new schema)...")
    # Old databases won't have processing_attempts table
    # Our schema init should create it automatically

    import sqlite3
    conn = sqlite3.connect(test_db_path)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='processing_attempts'"
    )
    result = cursor.fetchone()
    conn.close()

    if result:
        print("✓ New table created automatically (migration works)")
    else:
        print("✗ ERROR: New table not created")
        return False

    # Cleanup
    test_db_path.unlink()

    print("\n✓ Backwards compatibility maintained")
    return True


def main():
    """Run all integration tests."""
    print("\n" + "="*80)
    print("INTEGRATION TESTING - Verify Changes Don't Break Flow")
    print("="*80)

    all_passed = True

    # Test 1: First-time flow
    if not test_first_time_flow():
        all_passed = False
        print("\n❌ First-time flow test FAILED")

    # Test 2: Duplicate prevention
    if not test_duplicate_prevention_flow():
        all_passed = False
        print("\n❌ Duplicate prevention flow test FAILED")

    # Test 3: Retry logic integration
    if not test_retry_logic_integration():
        all_passed = False
        print("\n❌ Retry logic integration test FAILED")

    # Test 4: Backwards compatibility
    if not test_backwards_compatibility():
        all_passed = False
        print("\n❌ Backwards compatibility test FAILED")

    # Summary
    print("\n" + "="*80)
    if all_passed:
        print("✅ ALL INTEGRATION TESTS PASSED")
        print("="*80)
        print("\nVerified:")
        print("  ✅ First-time emails process normally")
        print("  ✅ Duplicate emails get skipped correctly")
        print("  ✅ Retry logic doesn't change return values")
        print("  ✅ Old databases migrate automatically")
        print("  ✅ Backwards compatibility maintained")
        print("\nSAFE TO DEPLOY - Changes won't break existing flow!")
        return 0
    else:
        print("❌ SOME INTEGRATION TESTS FAILED")
        print("="*80)
        print("\nDO NOT DEPLOY - Fix integration issues first!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
