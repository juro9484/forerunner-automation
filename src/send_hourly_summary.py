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
        # Query database for emails processed in last hour
        from email_database import EmailDatabase
        database = EmailDatabase()

        # Time period
        now = datetime.now()
        one_hour_ago = now - timedelta(hours=1)
        period_end = now.strftime('%Y-%m-%d %H:%M')
        period_start = one_hour_ago.strftime('%Y-%m-%d %H:%M')

        # Query database for hourly stats using context manager
        with database._get_connection() as conn:
            cursor = conn.cursor()

            # Count emails processed in last hour
            cursor.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
                FROM processed_emails
                WHERE processed_timestamp >= ?
            """, (one_hour_ago.isoformat(),))

            row = cursor.fetchone()
            total_processed = row[0] if row[0] else 0
            emails_processed = row[1] if row[1] else 0
            emails_failed = row[2] if row[2] else 0

            # Get breakdown by type (rough approximation based on claim_number)
            cursor.execute("""
                SELECT COUNT(*)
                FROM processed_emails
                WHERE processed_timestamp >= ?
                AND status = 'success'
                AND claim_number != 'N/A'
            """, (one_hour_ago.isoformat(),))
            notes_posted = cursor.fetchone()[0] or 0

            cursor.execute("""
                SELECT COUNT(*)
                FROM processed_emails
                WHERE processed_timestamp >= ?
                AND status = 'success'
                AND claim_number = 'N/A'
            """, (one_hour_ago.isoformat(),))
            claims_created = cursor.fetchone()[0] or 0

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
            notes_posted=notes_posted,
            claims_created=claims_created,
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
