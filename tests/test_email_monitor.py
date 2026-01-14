#!/usr/bin/env python3
"""
Standalone test script for email_monitor.py
This allows you to test the email monitoring functionality independently.
"""

import sys
import logging
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from email_monitor import EmailMonitor, EmailMonitorError
from config import Config

# Configure logging with detailed output
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/test_email_monitor.log"),
    ],
)

logger = logging.getLogger(__name__)


def main():
    """Test the email monitor."""
    logger.info("=" * 80)
    logger.info("Email Monitor Test Script")
    logger.info("=" * 80)

    # Validate configuration
    if not Config.validate():
        logger.error("Configuration validation failed. Please check your .env file.")
        logger.info("\nRequired environment variables:")
        logger.info("  - BOT_EMAIL_USER")
        logger.info("  - BOT_EMAIL_PASS")
        logger.info("  - BOT_EMAIL_IMAP_SERVER (optional, defaults to imap.gmail.com)")
        logger.info("  - BOT_EMAIL_IMAP_PORT (optional, defaults to 993)")
        return 1

    logger.info(f"\nConnecting to: {Config.BOT_EMAIL_USER}")
    logger.info(f"IMAP Server: {Config.BOT_EMAIL_IMAP_SERVER}:{Config.BOT_EMAIL_IMAP_PORT}")
    logger.info(f"Claim number pattern: {Config.CLAIM_NUMBER_PATTERN}\n")

    try:
        # Create email monitor with context manager (ensures cleanup)
        with EmailMonitor() as monitor:
            logger.info("Connection established successfully!\n")

            # Fetch and process unread emails
            emails = monitor.process_emails()

            if not emails:
                logger.info("No unread emails with claim numbers found.")
                return 0

            # Display results
            logger.info(f"\n{'=' * 80}")
            logger.info(f"Found {len(emails)} email(s) with claim numbers")
            logger.info(f"{'=' * 80}\n")

            for idx, email_data in enumerate(emails, 1):
                logger.info(f"\nEmail #{idx}:")
                logger.info(f"  Claim Number: #{email_data.claim_number}")
                logger.info(f"  From: {email_data.sender}")
                logger.info(f"  Subject: {email_data.subject}")
                logger.info(f"  Timestamp: {email_data.timestamp}")
                logger.info(f"  Email ID: {email_data.email_id}")
                logger.info(f"  Content Preview:")

                # Show first 300 characters of content
                content_preview = email_data.email_content[:300]
                for line in content_preview.split("\n"):
                    logger.info(f"    {line}")

                if len(email_data.email_content) > 300:
                    logger.info("    ...")

            # PRODUCTION NOTE: In production, you'll mark as read ONLY after successful processing
            # This test script asks for confirmation since we're not actually processing

            logger.info("\n" + "=" * 80)
            logger.info("PRODUCTION WORKFLOW:")
            logger.info("1. Fetch email (done)")
            logger.info("2. Summarize with AI (TODO)")
            logger.info("3. Post to Claim Titan (TODO)")
            logger.info("4. Mark in database as 'success' (TODO)")
            logger.info("5. Mark as read ← ONLY if steps 2-4 succeed")
            logger.info("=" * 80)

            response = input("\nMark these emails as read for testing? (y/n): ").lower().strip()

            if response == "y":
                for email_data in emails:
                    # In production, this only happens AFTER successful processing
                    monitor.mark_email_processed(email_data, status="success")
                    success = monitor.mark_as_read(email_data.email_id)
                    if success:
                        logger.info(f"✓ Marked email #{email_data.claim_number} as read")
                    else:
                        logger.error(f"✗ Failed to mark email #{email_data.claim_number} as read")
            else:
                logger.info("Emails left unread (they'll be fetched again next run)")

        logger.info("\nTest completed successfully!")
        return 0

    except EmailMonitorError as e:
        logger.error(f"\nEmail monitoring error: {e}")
        logger.info("\nTroubleshooting tips:")
        logger.info("  1. Verify your email credentials in .env file")
        logger.info("  2. For Gmail, ensure you're using an App Password, not your regular password")
        logger.info("     (https://support.google.com/accounts/answer/185833)")
        logger.info("  3. Check that IMAP is enabled in your email account settings")
        logger.info("  4. Verify firewall/network allows IMAP connections (port 993)")
        return 1

    except KeyboardInterrupt:
        logger.info("\nTest interrupted by user")
        return 0

    except Exception as e:
        logger.error(f"\nUnexpected error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
