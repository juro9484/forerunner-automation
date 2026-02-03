"""
Simple metrics tracking to text file.
Tracks emails processed, notes posted, claims created, success rates.
"""

import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict


class MetricsTracker:
    """
    Tracks processing metrics and writes to simple text file.
    Provides human-readable stats for monitoring.
    """

    def __init__(self, metrics_file: str = "logs/metrics.txt"):
        """
        Initialize metrics tracker.

        Args:
            metrics_file: Path to metrics text file
        """
        self.metrics_file = Path(metrics_file)
        self.metrics_file.parent.mkdir(parents=True, exist_ok=True)

        self.json_file = self.metrics_file.with_suffix('.json')
        self.logger = logging.getLogger(__name__)

        # Load existing metrics or initialize
        self.metrics = self._load_metrics()

    def _load_metrics(self) -> Dict:
        """Load metrics from JSON file or create new."""
        if self.json_file.exists():
            try:
                with open(self.json_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"Could not load metrics: {e}, starting fresh")

        # Default metrics structure
        return {
            "session_start": datetime.now().isoformat(),
            "last_reset": datetime.now().isoformat(),
            "total_emails": 0,
            "notes_posted": 0,
            "claims_created": 0,
            "successful": 0,
            "failed": 0,
            "last_update": datetime.now().isoformat()
        }

    def _save_metrics(self):
        """Save metrics to JSON file."""
        self.metrics["last_update"] = datetime.now().isoformat()

        try:
            with open(self.json_file, 'w') as f:
                json.dump(self.metrics, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save metrics: {e}")

    def _write_text_file(self):
        """Write human-readable metrics to text file."""
        try:
            success_rate = 0.0
            total = self.metrics["successful"] + self.metrics["failed"]
            if total > 0:
                success_rate = (self.metrics["successful"] / total) * 100

            content = f"""
{'='*80}
FORERUNNER CLAIMS AUTOMATION - METRICS
{'='*80}

Session Started: {self.metrics["session_start"]}
Last Updated:    {self.metrics["last_update"]}

PROCESSING STATS
{'='*80}
Total Emails Processed:  {self.metrics["total_emails"]}
Notes Posted:            {self.metrics["notes_posted"]}
Claims Created:          {self.metrics["claims_created"]}

SUCCESS RATE
{'='*80}
Successful:              {self.metrics["successful"]}
Failed:                  {self.metrics["failed"]}
Success Rate:            {success_rate:.1f}%

STATUS
{'='*80}
"""
            # Add status indicator
            if success_rate >= 95.0:
                content += "Status: 🟢 HEALTHY (Above SLA target of 95%)\n"
            elif success_rate >= 85.0:
                content += "Status: 🟡 DEGRADED (Below SLA target, above 85%)\n"
            else:
                content += "Status: 🔴 CRITICAL (Below 85% success rate)\n"

            content += f"\n{'='*80}\n"
            content += "View detailed logs: logs/monitor_daemon.log\n"
            content += f"{'='*80}\n"

            with open(self.metrics_file, 'w') as f:
                f.write(content)

        except Exception as e:
            self.logger.error(f"Failed to write metrics text file: {e}")

    def record_email_processed(self):
        """Record that an email was processed."""
        self.metrics["total_emails"] += 1
        self._save_metrics()
        self._write_text_file()

    def record_note_posted(self, success: bool = True):
        """Record that a note was posted to Claim Titan."""
        self.metrics["notes_posted"] += 1
        if success:
            self.metrics["successful"] += 1
        else:
            self.metrics["failed"] += 1
        self._save_metrics()
        self._write_text_file()

    def record_claim_created(self, success: bool = True):
        """Record that a claim was created in Claim Titan."""
        self.metrics["claims_created"] += 1
        if success:
            self.metrics["successful"] += 1
        else:
            self.metrics["failed"] += 1
        self._save_metrics()
        self._write_text_file()

    def record_failure(self):
        """Record a processing failure."""
        self.metrics["failed"] += 1
        self._save_metrics()
        self._write_text_file()

    def get_success_rate(self) -> float:
        """Get current success rate as percentage."""
        total = self.metrics["successful"] + self.metrics["failed"]
        if total == 0:
            return 100.0
        return (self.metrics["successful"] / total) * 100

    def get_stats(self) -> Dict:
        """Get current metrics as dictionary."""
        return {
            **self.metrics,
            "success_rate": self.get_success_rate()
        }

    def reset_daily(self):
        """Reset metrics at start of new day."""
        now = datetime.now()
        last_reset = datetime.fromisoformat(self.metrics["last_reset"])

        # Check if it's a new day
        if now.date() > last_reset.date():
            self.logger.info(f"New day detected, resetting daily metrics")

            self.metrics = {
                "session_start": now.isoformat(),
                "last_reset": now.isoformat(),
                "total_emails": 0,
                "notes_posted": 0,
                "claims_created": 0,
                "successful": 0,
                "failed": 0,
                "last_update": now.isoformat()
            }

            self._save_metrics()
            self._write_text_file()

            self.logger.info("Daily metrics reset complete")


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    tracker = MetricsTracker()

    # Simulate some activity
    tracker.record_email_processed()
    tracker.record_note_posted(success=True)
    tracker.record_email_processed()
    tracker.record_claim_created(success=True)
    tracker.record_email_processed()
    tracker.record_note_posted(success=False)

    print(f"\nMetrics saved to: {tracker.metrics_file}")
    print(f"\nCurrent stats: {tracker.get_stats()}")
