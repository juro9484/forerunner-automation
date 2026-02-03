#!/usr/bin/env python3
"""
Test Phase 2 features: Health checks, metrics tracking, browser deadlocks.
"""

import sys
import logging
import time
from pathlib import Path
from datetime import datetime

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from metrics_tracker import MetricsTracker
from health_checker import HealthChecker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def test_metrics_tracking():
    """Test metrics tracking and text file generation."""
    print("\n" + "="*80)
    print("TEST 1: Metrics Tracking")
    print("="*80)

    # Create test metrics tracker
    metrics = MetricsTracker(metrics_file="logs/test_metrics.txt")

    print("\n[Test 1a] Recording sample activity...")

    # Simulate processing
    metrics.record_email_processed()
    metrics.record_note_posted(success=True)
    print("  ✓ Recorded: 1 email, 1 note posted (success)")

    metrics.record_email_processed()
    metrics.record_claim_created(success=True)
    print("  ✓ Recorded: 1 email, 1 claim created (success)")

    metrics.record_email_processed()
    metrics.record_note_posted(success=False)
    print("  ✓ Recorded: 1 email, 1 note posted (failed)")

    # Check success rate
    success_rate = metrics.get_success_rate()
    print(f"\n[Test 1b] Success rate calculation: {success_rate:.1f}%")

    expected_rate = (2 / 3) * 100  # 2 successful, 1 failed
    if abs(success_rate - expected_rate) < 0.1:
        print(f"✓ Success rate correct (expected {expected_rate:.1f}%)")
    else:
        print(f"✗ ERROR: Success rate wrong (expected {expected_rate:.1f}%, got {success_rate:.1f}%)")
        return False

    # Check text file was created
    metrics_file = Path("logs/test_metrics.txt")
    if metrics_file.exists():
        print(f"\n[Test 1c] Metrics text file created: {metrics_file}")
        with open(metrics_file, 'r') as f:
            content = f.read()
            if "Total Emails Processed:" in content and "Success Rate:" in content:
                print("✓ Text file format is correct")
                print("\nSample content:")
                print("-" * 40)
                print(content[:400])
                print("-" * 40)
            else:
                print("✗ ERROR: Text file format is wrong")
                return False
    else:
        print("✗ ERROR: Metrics text file not created")
        return False

    # Cleanup
    metrics_file.unlink()
    Path("logs/test_metrics.json").unlink()

    print("\n✓ All metrics tracking tests PASSED")
    return True


def test_health_checking():
    """Test health checking and stuck detection."""
    print("\n" + "="*80)
    print("TEST 2: Health Checking")
    print("="*80)

    # Create test health checker
    health = HealthChecker(health_file="logs/test_health.json")

    print("\n[Test 2a] Testing successful checks...")
    health.record_check_start()
    health.record_check_success(emails_processed=5)

    if health.health["status"] == "healthy":
        print("✓ Status is 'healthy' after success")
    else:
        print(f"✗ ERROR: Status should be 'healthy', got '{health.health['status']}'")
        return False

    if health.health["consecutive_failures"] == 0:
        print("✓ Consecutive failures reset to 0")
    else:
        print(f"✗ ERROR: Consecutive failures should be 0, got {health.health['consecutive_failures']}")
        return False

    print("\n[Test 2b] Testing failure tracking...")
    health.record_check_failure("Test error 1")
    health.record_check_failure("Test error 2")
    health.record_check_failure("Test error 3")

    if health.health["consecutive_failures"] == 3:
        print("✓ Consecutive failures tracked correctly (3)")
    else:
        print(f"✗ ERROR: Should have 3 failures, got {health.health['consecutive_failures']}")
        return False

    if health.health["status"] == "degraded":
        print("✓ Status changed to 'degraded' after 3 failures")
    else:
        print(f"✗ ERROR: Status should be 'degraded', got '{health.health['status']}'")
        return False

    print("\n[Test 2c] Testing alert threshold...")
    health.record_check_failure("Test error 4")
    health.record_check_failure("Test error 5")

    alert_message = health.should_alert()
    if alert_message and "5 consecutive" in alert_message:
        print("✓ Alert triggered at 5 consecutive failures")
        print(f"  Alert message: {alert_message[:100]}...")
    else:
        print("✗ ERROR: Should alert at 5 consecutive failures")
        return False

    print("\n[Test 2d] Testing recovery...")
    health.record_check_success(emails_processed=2)

    if health.health["consecutive_failures"] == 0:
        print("✓ Consecutive failures reset after success")
    else:
        print(f"✗ ERROR: Failures should reset, got {health.health['consecutive_failures']}")
        return False

    if health.health["status"] == "healthy":
        print("✓ Status back to 'healthy' after recovery")
    else:
        print(f"✗ ERROR: Status should be 'healthy', got '{health.health['status']}'")
        return False

    print("\n[Test 2e] Testing status summary...")
    summary = health.get_status_summary()
    if "🟢" in summary and "HEALTHY" in summary:
        print("✓ Status summary format correct")
    else:
        print("✗ ERROR: Status summary format wrong")
        return False

    # Cleanup
    Path("logs/test_health.json").unlink()

    print("\n✓ All health checking tests PASSED")
    return True


def test_sla_tracking():
    """Test SLA tracking logic."""
    print("\n" + "="*80)
    print("TEST 3: SLA Tracking")
    print("="*80)

    metrics = MetricsTracker(metrics_file="logs/test_sla_metrics.txt")

    print("\n[Test 3a] Testing above SLA threshold (95%)...")

    # Simulate 95% success rate: 19 successful, 1 failed
    for i in range(19):
        metrics.record_note_posted(success=True)
    metrics.record_note_posted(success=False)

    success_rate = metrics.get_success_rate()
    if success_rate >= 95.0:
        print(f"✓ Success rate above SLA: {success_rate:.1f}%")
    else:
        print(f"✗ ERROR: Success rate should be >= 95%, got {success_rate:.1f}%")
        return False

    print("\n[Test 3b] Testing below SLA threshold...")

    # Add more failures to drop below 95%: now 19 successful, 3 failed = 86.4%
    metrics.record_note_posted(success=False)
    metrics.record_note_posted(success=False)

    success_rate = metrics.get_success_rate()
    if success_rate < 95.0:
        print(f"✓ Success rate below SLA: {success_rate:.1f}% (should trigger alert)")
    else:
        print(f"✗ ERROR: Success rate should be < 95%, got {success_rate:.1f}%")
        return False

    # Cleanup
    Path("logs/test_sla_metrics.txt").unlink()
    Path("logs/test_sla_metrics.json").unlink()

    print("\n✓ All SLA tracking tests PASSED")
    return True


def main():
    """Run all Phase 2 tests."""
    print("\n" + "="*80)
    print("PHASE 2 TESTING - Health & Metrics")
    print("="*80)

    all_passed = True

    # Test 1: Metrics tracking
    if not test_metrics_tracking():
        all_passed = False
        print("\n❌ Metrics tracking test FAILED")

    # Test 2: Health checking
    if not test_health_checking():
        all_passed = False
        print("\n❌ Health checking test FAILED")

    # Test 3: SLA tracking
    if not test_sla_tracking():
        all_passed = False
        print("\n❌ SLA tracking test FAILED")

    # Summary
    print("\n" + "="*80)
    if all_passed:
        print("✅ ALL PHASE 2 TESTS PASSED")
        print("="*80)
        print("\nYou can now view metrics at: logs/metrics.txt")
        print("Health status at: logs/health.json")
        print("\nSafe to commit and deploy!")
        return 0
    else:
        print("❌ SOME TESTS FAILED")
        print("="*80)
        print("\nDO NOT deploy until tests pass!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
