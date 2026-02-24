#!/usr/bin/env python3
"""
Hourly summary email script.
Reads metrics from the last hour and sends summary email.
Run via cron every hour.
"""

import sys
import logging
from pathlib import Path
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from email_notifier import EmailNotifier
from metrics_tracker import MetricsTracker


def main():
    """Send hourly summary email."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)

    try:
        # Read metrics from last hour
        metrics = MetricsTracker()

        # Get hourly stats (MetricsTracker stores daily, so we approximate)
        # In production, you'd read from database for exact hourly counts
        # For now, we'll use the daily metrics as a proxy
        notes_posted_success = getattr(metrics, 'notes_posted_success', 0)
        notes_posted_failed = getattr(metrics, 'notes_posted_failed', 0)
        claims_created_success = getattr(metrics, 'claims_created_success', 0)
        claims_created_failed = getattr(metrics, 'claims_created_failed', 0)

        emails_processed = notes_posted_success + claims_created_success
        emails_failed = notes_posted_failed + claims_created_failed

        # Time period
        now = datetime.now()
        period_end = now.strftime('%Y-%m-%d %H:%M')
        period_start = (now - timedelta(hours=1)).strftime('%Y-%m-%d %H:%M')

        # Initialize email notifier
        notifier = EmailNotifier(
            smtp_server=Config.NOTIFICATION_SMTP_SERVER,
            smtp_port=Config.NOTIFICATION_SMTP_PORT,
            from_email=Config.NOTIFICATION_FROM_EMAIL,
            from_password=Config.NOTIFICATION_FROM_PASSWORD,
            to_emails=Config.NOTIFICATION_TO_EMAILS
        )

        # Send summary
        success = notifier.send_hourly_summary(
            client_id=Config.CLIENT_ID,
            emails_processed=emails_processed,
            emails_failed=emails_failed,
            notes_posted=notes_posted_success,
            claims_created=claims_created_success,
            period_start=period_start,
            period_end=period_end
        )

        if success:
            logger.info("Hourly summary email sent successfully")
            return 0
        else:
            logger.error("Failed to send hourly summary email")
            return 1

    except Exception as e:
        logger.error(f"Error sending hourly summary: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
