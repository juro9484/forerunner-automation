"""
Health check system for monitoring daemon status.
Detects stuck daemon, consecutive failures, and unhealthy states.
"""

import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional


class HealthChecker:
    """
    Monitors system health and detects issues.
    Tracks check times, failures, and alerts on unhealthy conditions.
    """

    def __init__(self, health_file: str = "logs/health.json"):
        """
        Initialize health checker.

        Args:
            health_file: Path to health status JSON file
        """
        self.health_file = Path(health_file)
        self.health_file.parent.mkdir(parents=True, exist_ok=True)

        self.logger = logging.getLogger(__name__)

        # Load existing health status or initialize
        self.health = self._load_health()

    def _load_health(self) -> dict:
        """Load health status from file or create new."""
        if self.health_file.exists():
            try:
                with open(self.health_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"Could not load health status: {e}, starting fresh")

        # Default health structure
        return {
            "daemon_started": datetime.now().isoformat(),
            "last_check_time": None,
            "last_success_time": None,
            "consecutive_failures": 0,
            "total_checks": 0,
            "total_failures": 0,
            "status": "starting"
        }

    def _save_health(self):
        """Save health status to file."""
        try:
            with open(self.health_file, 'w') as f:
                json.dump(self.health, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save health status: {e}")

    def record_check_start(self):
        """Record that a check is starting."""
        self.health["last_check_time"] = datetime.now().isoformat()
        self.health["total_checks"] += 1
        self._save_health()

    def record_check_success(self, emails_processed: int = 0):
        """
        Record successful check completion.

        Args:
            emails_processed: Number of emails processed in this check
        """
        self.health["last_success_time"] = datetime.now().isoformat()
        self.health["consecutive_failures"] = 0
        self.health["status"] = "healthy"

        self._save_health()
        self.logger.debug(f"Health check: OK (processed {emails_processed} emails)")

    def record_check_failure(self, error_message: str):
        """
        Record failed check.

        Args:
            error_message: Description of the failure
        """
        self.health["consecutive_failures"] += 1
        self.health["total_failures"] += 1
        self.health["last_error"] = error_message
        self.health["last_error_time"] = datetime.now().isoformat()

        # Update status based on failure count
        if self.health["consecutive_failures"] >= 5:
            self.health["status"] = "critical"
        elif self.health["consecutive_failures"] >= 3:
            self.health["status"] = "degraded"
        else:
            self.health["status"] = "warning"

        self._save_health()
        self.logger.warning(
            f"Health check: FAILED (consecutive failures: {self.health['consecutive_failures']})"
        )

    def is_stuck(self, timeout_minutes: int = 10) -> bool:
        """
        Check if daemon appears stuck (no checks in timeout period).

        Args:
            timeout_minutes: Minutes without check to consider stuck

        Returns:
            True if daemon appears stuck, False otherwise
        """
        if not self.health["last_check_time"]:
            return False

        last_check = datetime.fromisoformat(self.health["last_check_time"])
        minutes_since_check = (datetime.now() - last_check).total_seconds() / 60

        return minutes_since_check > timeout_minutes

    def is_unhealthy(self) -> bool:
        """
        Check if system is unhealthy.

        Returns:
            True if unhealthy (3+ consecutive failures or stuck), False otherwise
        """
        return (
            self.health["consecutive_failures"] >= 3
            or self.is_stuck()
            or self.health["status"] in ["critical", "degraded"]
        )

    def get_status_summary(self) -> str:
        """
        Get human-readable health status summary.

        Returns:
            Status string with health details
        """
        status_emoji = {
            "starting": "🔵",
            "healthy": "🟢",
            "warning": "🟡",
            "degraded": "🟠",
            "critical": "🔴"
        }

        emoji = status_emoji.get(self.health["status"], "⚪")
        status = self.health["status"].upper()

        summary = f"{emoji} {status}\n"
        summary += f"Last Check: {self.health['last_check_time'] or 'Never'}\n"
        summary += f"Last Success: {self.health['last_success_time'] or 'Never'}\n"
        summary += f"Consecutive Failures: {self.health['consecutive_failures']}\n"

        # Check if stuck
        if self.is_stuck():
            minutes = (datetime.now() - datetime.fromisoformat(self.health["last_check_time"])).total_seconds() / 60
            summary += f"⚠️  DAEMON APPEARS STUCK (no check in {minutes:.0f} minutes)\n"

        return summary

    def should_alert(self) -> Optional[str]:
        """
        Check if we should send an alert.

        Returns:
            Alert message if alert needed, None otherwise
        """
        # Alert on 5 consecutive failures
        if self.health["consecutive_failures"] == 5:
            return (
                f"CRITICAL: 5 consecutive check failures\n"
                f"Last success: {self.health['last_success_time']}\n"
                f"Last error: {self.health.get('last_error', 'Unknown')}"
            )

        # Alert if stuck (no checks in 10 minutes)
        if self.is_stuck(timeout_minutes=10):
            minutes = (datetime.now() - datetime.fromisoformat(self.health["last_check_time"])).total_seconds() / 60
            return (
                f"CRITICAL: Daemon appears STUCK\n"
                f"No check in {minutes:.0f} minutes\n"
                f"Last check: {self.health['last_check_time']}"
            )

        return None

    def get_health_data(self) -> dict:
        """Get current health data as dictionary."""
        return {
            **self.health,
            "is_stuck": self.is_stuck(),
            "is_unhealthy": self.is_unhealthy()
        }


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    checker = HealthChecker()

    # Simulate some checks
    checker.record_check_start()
    checker.record_check_success(emails_processed=3)

    print("\nHealth Status:")
    print(checker.get_status_summary())

    print(f"\nHealth data saved to: {checker.health_file}")
