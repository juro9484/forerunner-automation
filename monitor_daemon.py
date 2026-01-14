#!/usr/bin/env python3
"""
Continuous email monitoring daemon.
Runs indefinitely, checking for new emails every 5 minutes.
"""

import sys
import time
import logging
import signal
from pathlib import Path
from datetime import datetime

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from email_monitor import EmailMonitor, EmailMonitorError
from config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/monitor_daemon.log"),
    ],
)

logger = logging.getLogger(__name__)

# Global flag for graceful shutdown
running = True


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global running
    logger.info("Shutdown signal received. Stopping monitor...")
    running = False


def main():
    """Main monitoring loop."""
    global running

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # kill command

    logger.info("=" * 80)
    logger.info("Email Monitor Daemon Starting")
    logger.info("=" * 80)
    logger.info(f"Monitoring: {Config.BOT_EMAIL_USER}")
    logger.info(f"Check interval: {Config.EMAIL_CHECK_INTERVAL} seconds")
    logger.info(f"Claim pattern: {Config.CLAIM_NUMBER_PATTERN}")
    logger.info(f"OAuth enabled: {Config.USE_OAUTH}")
    logger.info("=" * 80)
    logger.info("Press Ctrl+C to stop\n")

    check_count = 0
    total_emails_processed = 0

    while running:
        check_count += 1
        logger.info(f"\n[Check #{check_count}] Starting email check at {datetime.now()}")

        try:
            # Connect and check emails
            with EmailMonitor() as monitor:
                emails = monitor.process_emails()

                if emails:
                    logger.info(f"✓ Found {len(emails)} new email(s) with claim numbers")

                    for email_data in emails:
                        logger.info(f"\n  Claim #{email_data.claim_number}")
                        logger.info(f"  From: {email_data.sender}")
                        logger.info(f"  Subject: {email_data.subject}")
                        logger.info(f"  Content preview: {email_data.email_content[:100]}...")

                        # In MVP: Just log and mark as processed
                        # TODO: Add AI summarization and Claim Titan posting here

                        # Mark as processed in database
                        monitor.mark_email_processed(email_data, status="success")

                        # Mark as read in email (only after success)
                        monitor.mark_as_read(email_data.email_id)

                        total_emails_processed += 1
                        logger.info(f"  ✓ Processed successfully")

                else:
                    logger.info("No new emails with claim numbers")

        except EmailMonitorError as e:
            logger.error(f"✗ Email monitoring error: {e}")
            logger.info("Will retry on next check...")

        except Exception as e:
            logger.error(f"✗ Unexpected error: {e}", exc_info=True)
            logger.info("Will retry on next check...")

        # Summary
        logger.info(f"\n[Check #{check_count}] Complete. Total processed: {total_emails_processed}")

        # Wait before next check (or exit if shutdown requested)
        if running:
            logger.info(f"Sleeping for {Config.EMAIL_CHECK_INTERVAL} seconds...")
            time.sleep(Config.EMAIL_CHECK_INTERVAL)

    logger.info("\n" + "=" * 80)
    logger.info("Email Monitor Daemon Stopped")
    logger.info(f"Total emails processed: {total_emails_processed}")
    logger.info(f"Total checks performed: {check_count}")
    logger.info("=" * 80)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\nShutdown requested by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
