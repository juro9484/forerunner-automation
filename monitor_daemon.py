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
from summarizer import EmailSummarizer, SummarizerError
from claim_titan_bot import ClaimTitanBot, ClaimTitanError
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
claim_titan_bot = None


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global running, claim_titan_bot
    logger.info("Shutdown signal received. Stopping monitor...")
    running = False

    # Cleanup bot if running
    if claim_titan_bot:
        try:
            claim_titan_bot.disconnect()
            logger.info("✓ Claim Titan bot disconnected")
        except Exception as e:
            logger.warning(f"Error disconnecting bot: {e}")


def main():
    """Main monitoring loop."""
    global running

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # kill command

    logger.info("=" * 80)
    logger.info("Forerunner Claims Automation - Email Monitor Daemon")
    logger.info("=" * 80)
    logger.info(f"Monitoring: {Config.BOT_EMAIL_USER}")
    logger.info(f"Check interval: {Config.EMAIL_CHECK_INTERVAL} seconds")
    logger.info(f"Claim pattern: {Config.CLAIM_NUMBER_PATTERN}")
    logger.info(f"OAuth enabled: {Config.USE_OAUTH}")
    logger.info(f"AI Provider: {Config.AI_PROVIDER}")
    logger.info(f"AI Summarization: ENABLED")
    logger.info(f"CRM Integration: Claim Titan (ENABLED)")
    logger.info("=" * 80)
    logger.info("Press Ctrl+C to stop\n")

    check_count = 0
    total_emails_processed = 0

    # Initialize summarizer once
    try:
        summarizer = EmailSummarizer()
        logger.info("✓ AI Summarizer initialized successfully")
    except Exception as e:
        logger.error(f"✗ Failed to initialize summarizer: {e}")
        logger.error("Cannot continue without summarizer. Check your ANTHROPIC_API_KEY in .env")
        return

    # Initialize Claim Titan bot once (keep browser alive for efficiency)
    global claim_titan_bot
    logger.info("DEBUG: About to initialize Claim Titan bot...")
    try:
        logger.info("DEBUG: Creating ClaimTitanBot instance...")
        claim_titan_bot = ClaimTitanBot()
        logger.info("DEBUG: Calling connect()...")
        claim_titan_bot.connect()
        logger.info("✓ Claim Titan bot initialized and logged in successfully")
    except Exception as e:
        logger.error(f"✗ Failed to initialize Claim Titan bot: {e}")
        logger.error(f"DEBUG: Exception type: {type(e).__name__}")
        logger.error(f"DEBUG: Exception details: {str(e)}")
        import traceback
        logger.error(f"DEBUG: Traceback:\n{traceback.format_exc()}")
        logger.error("Will continue without CRM posting. Check CLAIM_TITAN credentials in .env")
        claim_titan_bot = None

    logger.info("")  # Blank line for readability

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

                        # Generate AI summary
                        try:
                            logger.info(f"  Generating AI summary...")
                            summary = summarizer.summarize_email(email_data)

                            # Log the summary in CRM format
                            logger.info(f"\n  " + "="*70)
                            logger.info(f"  CLAIM TITAN NOTE - Claim #{email_data.claim_number}")
                            logger.info(f"  " + "="*70)
                            for line in summarizer.format_for_crm(summary).split('\n'):
                                logger.info(f"  {line}")
                            logger.info(f"  " + "="*70)
                            logger.info(f"  Model: {summary.model_used}")
                            logger.info(f"  Generated: {summary.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
                            logger.info(f"  " + "="*70 + "\n")

                            # Post to Claim Titan CRM
                            if claim_titan_bot:
                                try:
                                    logger.info(f"  Posting note to Claim Titan...")
                                    result = claim_titan_bot.post_note(
                                        claim_number=summary.claim_number,
                                        title=summary.title,
                                        description=summary.description
                                    )

                                    if result.success:
                                        logger.info(f"  ✓ Posted to Claim Titan successfully")
                                    else:
                                        logger.error(f"  ✗ Failed to post to Claim Titan: {result.error_message}")
                                        if result.screenshot_path:
                                            logger.error(f"  Screenshot: {result.screenshot_path}")

                                except ClaimTitanError as e:
                                    logger.error(f"  ✗ Claim Titan error: {e}")
                                    logger.error(f"  Note was not posted to CRM, but will continue processing")

                                except Exception as e:
                                    logger.error(f"  ✗ Unexpected error posting to Claim Titan: {e}")
                                    logger.error(f"  Note was not posted to CRM, but will continue processing")

                                # Handle attachments if any
                                if email_data.attachments and claim_titan_bot:
                                    try:
                                        logger.info(f"  Processing {len(email_data.attachments)} attachment(s)...")

                                        # Upload attachments (or log in test mode)
                                        # Returns dict mapping filename -> folder_name (or "Failed" if failed)
                                        upload_results = claim_titan_bot.upload_attachments(
                                            attachments=email_data.attachments,
                                            claim_number=email_data.claim_number,
                                            email_summary=summary.description
                                        )

                                        # Save attachment metadata to database
                                        for attachment in email_data.attachments:
                                            filename = attachment.filename
                                            folder = upload_results.get(filename, "Unknown")

                                            # Determine if upload was successful
                                            uploaded = folder not in ["Failed", "Unknown"]

                                            # Move to permanent storage
                                            try:
                                                permanent_path = claim_titan_bot.attachment_handler.move_to_permanent_storage(
                                                    attachment=attachment,
                                                    claim_number=email_data.claim_number,
                                                    folder_name=folder if folder not in ["Failed", "Unknown"] else "Other"
                                                )

                                                # Save to database
                                                monitor.db.save_attachment(
                                                    email_id=email_data.email_id,
                                                    claim_number=email_data.claim_number,
                                                    original_filename=attachment.filename,
                                                    saved_filename=permanent_path.split('/')[-1],
                                                    file_path=permanent_path,
                                                    file_size=attachment.file_size,
                                                    content_type=attachment.content_type,
                                                    category=attachment.category,
                                                    ai_description=attachment.description,
                                                    crm_folder=folder if folder not in ["Failed", "Unknown"] else None,
                                                    uploaded_to_crm=uploaded
                                                )

                                                logger.info(f"  ✓ Saved {filename} to {permanent_path}")

                                            except Exception as e:
                                                logger.error(f"  ✗ Error saving {filename}: {e}")

                                        logger.info(f"  ✓ Processed all attachments")

                                    except Exception as e:
                                        logger.error(f"  ✗ Error processing attachments: {e}")
                                        logger.error(f"  Attachments not uploaded, but will continue processing")

                            else:
                                logger.warning(f"  ⚠ Claim Titan bot not available, skipping CRM post")

                            # Mark as processed in database
                            monitor.mark_email_processed(email_data, status="success")

                            # Mark as read in email (only after success)
                            monitor.mark_as_read(email_data.email_id)

                            total_emails_processed += 1
                            logger.info(f"  ✓ Processed successfully")

                        except SummarizerError as e:
                            logger.error(f"  ✗ Summarization failed: {e}")
                            monitor.mark_email_processed(email_data, status="failed", error_message=str(e))
                            logger.info(f"  Email marked as failed in database")

                        except Exception as e:
                            logger.error(f"  ✗ Unexpected error during processing: {e}", exc_info=True)
                            monitor.mark_email_processed(email_data, status="failed", error_message=str(e))
                            logger.info(f"  Email marked as failed in database")

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

    # Cleanup bot before exit
    if claim_titan_bot:
        try:
            claim_titan_bot.disconnect()
            logger.info("✓ Claim Titan bot disconnected")
        except Exception as e:
            logger.warning(f"Error disconnecting bot: {e}")

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
