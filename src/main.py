"""
Main orchestrator for Forerunner Claims Automation.
Coordinates email monitoring, AI summarization, and CRM automation.
"""

import logging
import sys
import traceback
import requests
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from adapters.email.outlook.adapter import OutlookAdapter
from adapters.crm.claim_titan.adapter import ClaimTitanAdapter
from summarizer import EmailSummarizer
from contract_parser import ContractParser
from check_parser import CheckParser
from email_database import EmailDatabase
from health_checker import HealthChecker
from metrics_tracker import MetricsTracker
from email_notifier import EmailNotifier


def setup_logging():
    """Configure logging for the application."""
    # Create client-specific log file if CLIENT_ID is set
    client_id = getattr(Config, 'CLIENT_ID', 'forerunner_claims')
    log_file = Config.LOGS_DIR / f"{client_id}.log"

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, Config.LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()  # Also log to console
        ]
    )

    logger = logging.getLogger(__name__)
    logger.info("="*80)
    logger.info("FORERUNNER CLAIMS AUTOMATION STARTING")
    logger.info(f"Client: {client_id}")
    logger.info(f"Log file: {log_file}")
    logger.info("="*80)

    return logger


def ping_healthchecks(status: str = ""):
    """
    Ping Healthchecks.io to indicate service is running.

    Args:
        status: Either "" (success), "/fail" (failure), or "/start" (starting)
    """
    if not Config.HEALTHCHECKS_ENABLED or not Config.HEALTHCHECKS_PING_URL:
        return

    try:
        url = Config.HEALTHCHECKS_PING_URL + status
        requests.get(url, timeout=10)
    except Exception as e:
        logging.getLogger(__name__).warning(f"Failed to ping Healthchecks.io: {e}")


def send_failure_notification(error_message: str, error_details: str = None):
    """
    Send email notification about service failure.

    Args:
        error_message: Brief error description
        error_details: Full error traceback
    """
    if not Config.NOTIFICATIONS_ENABLED:
        return

    try:
        notifier = EmailNotifier(
            smtp_server=Config.NOTIFICATION_SMTP_SERVER,
            smtp_port=Config.NOTIFICATION_SMTP_PORT,
            from_email=Config.NOTIFICATION_FROM_EMAIL,
            from_password=Config.NOTIFICATION_FROM_PASSWORD,
            to_emails=Config.NOTIFICATION_TO_EMAILS
        )

        notifier.send_failure_alert(
            client_id=Config.CLIENT_ID,
            error_message=error_message,
            error_details=error_details
        )
    except Exception as e:
        logging.getLogger(__name__).error(f"Failed to send notification email: {e}")


def send_startup_notification():
    """Send startup notification to verify email is working."""
    if not Config.NOTIFICATIONS_ENABLED:
        return

    try:
        notifier = EmailNotifier(
            smtp_server=Config.NOTIFICATION_SMTP_SERVER,
            smtp_port=Config.NOTIFICATION_SMTP_PORT,
            from_email=Config.NOTIFICATION_FROM_EMAIL,
            from_password=Config.NOTIFICATION_FROM_PASSWORD,
            to_emails=Config.NOTIFICATION_TO_EMAILS
        )

        notifier.send_success_alert(
            client_id=Config.CLIENT_ID,
            message="Service Started Successfully",
            details="Email notifications are working correctly. You will receive alerts if the service fails."
        )
        logging.getLogger(__name__).info("Startup notification sent")
    except Exception as e:
        logging.getLogger(__name__).error(f"Failed to send startup notification: {e}")


def main():
    """Main application loop."""
    logger = setup_logging()

    # Initialize health checker and metrics
    health = HealthChecker()
    metrics = MetricsTracker()

    try:
        # Validate configuration
        if not Config.validate():
            logger.error("Configuration validation failed. Check .env file.")
            return 1

        health.record_check_start()
        ping_healthchecks("/start")

        logger.info("Initializing components...")

        # Initialize email adapter (Outlook)
        logger.info(f"Email adapter: Outlook")
        email_adapter = OutlookAdapter()

        # Initialize CRM adapter (Claim Titan) - loads features based on config
        logger.info(f"CRM adapter: Claim Titan")
        crm_adapter = ClaimTitanAdapter(config=Config)

        # Initialize AI components
        summarizer = EmailSummarizer()
        contract_parser = ContractParser()
        check_parser = CheckParser()

        # Initialize database
        database = EmailDatabase()

        logger.info("✓ All components initialized")

        # Main processing loop
        logger.info("Starting email processing...")

        with email_adapter as email:
            emails = email.fetch_unread_emails()
            logger.info(f"Retrieved {len(emails)} email(s) for processing")

            if not emails:
                logger.info("No emails to process")
                health.record_check_success(emails_processed=0)
                return 0

            with crm_adapter as crm:
                processed_count = 0
                failed_count = 0

                for email_data in emails:
                    try:
                        logger.info("="*80)
                        logger.info(f"Processing email: {email_data.subject}")
                        logger.info(f"  From: {email_data.sender}")
                        logger.info(f"  Claim: {email_data.claim_number or 'N/A (contract email)'}")
                        logger.info("="*80)

                        # Check if already processed
                        if database.is_processed(email_data.email_id):
                            logger.info(f"Email {email_data.email_id} already processed, skipping")
                            email.mark_as_read(email_data.email_id)
                            continue

                        # Determine email type based on subject keywords
                        subject_lower = email_data.subject.lower()

                        # Check keywords
                        check_keywords = [
                            "check",
                            "checks",
                            "payment",
                            "new check",
                            "carrier check",
                            "new payment"
                        ]
                        is_check = any(keyword in subject_lower for keyword in check_keywords)

                        # Contract keywords (removed "new" to avoid conflicts with "new check")
                        contract_keywords = [
                            "contract",
                            "new claim",
                            "new contract",
                            "add claim",
                            "create claim",
                            "add contract"
                        ]
                        is_contract = any(keyword in subject_lower for keyword in contract_keywords) and not is_check

                        if is_check:
                            # Process as check deposit (add carrier checks)
                            logger.info("Processing as CHECK DEPOSIT email...")

                            check_feature = crm.get_feature('check_deposit')
                            if not check_feature:
                                logger.warning("Check deposit feature not enabled, skipping")
                                continue

                            # Find all PDF attachments (each PDF = one check)
                            if not email_data.attachments:
                                logger.warning("Check email has no attachments, skipping")
                                continue

                            pdf_attachments = [att for att in email_data.attachments
                                             if att.filename.lower().endswith('.pdf')]
                            if not pdf_attachments:
                                logger.warning("No PDF attachments found in check email")
                                continue

                            logger.info(f"Found {len(pdf_attachments)} check PDF(s) to process")

                            checks_processed = 0
                            checks_failed = 0

                            # Process each check PDF
                            for pdf_attachment in pdf_attachments:
                                try:
                                    logger.info(f"\n  Processing check: {pdf_attachment.filename}")

                                    # Parse check data
                                    check_data = check_parser.parse_check(pdf_attachment.file_path)
                                    if not check_data:
                                        logger.error(f"  ✗ Failed to parse check: {pdf_attachment.filename}")
                                        checks_failed += 1
                                        continue

                                    # Check confidence threshold
                                    if check_data.overall_confidence < 80:
                                        logger.warning(f"  ✗ Check confidence too low ({check_data.overall_confidence}%) - skipping auto-processing")
                                        logger.warning(f"      Manual review required for: {pdf_attachment.filename}")
                                        checks_failed += 1

                                        # Send low confidence alert
                                        try:
                                            notifier = EmailNotifier(
                                                smtp_server=Config.NOTIFICATION_SMTP_SERVER,
                                                smtp_port=Config.NOTIFICATION_SMTP_PORT,
                                                from_email=Config.NOTIFICATION_FROM_EMAIL,
                                                from_password=Config.NOTIFICATION_FROM_PASSWORD,
                                                to_emails=Config.NOTIFICATION_TO_EMAILS
                                            )
                                            notifier.send_check_alert(
                                                client_id=Config.CLIENT_ID,
                                                alert_type="low_confidence",
                                                check_filename=pdf_attachment.filename,
                                                check_amount=check_data.check_amount,
                                                claim_number=check_data.claim_number,
                                                confidence_score=check_data.overall_confidence,
                                                payer=check_data.payer
                                            )
                                            logger.info(f"  ✓ Sent low confidence alert email")
                                        except Exception as e:
                                            logger.error(f"  ! Failed to send low confidence alert: {e}")

                                        continue

                                    # Add check to ClaimTitan
                                    result = check_feature.process(check_data, pdf_attachment.file_path)

                                    if result.success:
                                        logger.info(f"  ✓ Added check ${check_data.check_amount} to claim {check_data.claim_number}")
                                        checks_processed += 1
                                        metrics.record_check_deposited(success=True)

                                        # Clean up: Delete check PDF after successful upload
                                        try:
                                            from pathlib import Path
                                            pdf_path = Path(pdf_attachment.file_path) if isinstance(pdf_attachment.file_path, str) else pdf_attachment.file_path
                                            pdf_path.unlink()
                                            logger.info(f"  ✓ Deleted check PDF: {pdf_attachment.filename}")
                                        except Exception as e:
                                            logger.warning(f"  ! Failed to delete check PDF: {e}")

                                    else:
                                        logger.error(f"  ✗ Failed to add check: {result.error_message}")
                                        checks_failed += 1
                                        metrics.record_check_deposited(success=False)

                                        # Send processing failure alert
                                        try:
                                            notifier = EmailNotifier(
                                                smtp_server=Config.NOTIFICATION_SMTP_SERVER,
                                                smtp_port=Config.NOTIFICATION_SMTP_PORT,
                                                from_email=Config.NOTIFICATION_FROM_EMAIL,
                                                from_password=Config.NOTIFICATION_FROM_PASSWORD,
                                                to_emails=Config.NOTIFICATION_TO_EMAILS
                                            )
                                            notifier.send_check_alert(
                                                client_id=Config.CLIENT_ID,
                                                alert_type="processing_failed",
                                                check_filename=pdf_attachment.filename,
                                                check_amount=check_data.check_amount,
                                                claim_number=check_data.claim_number,
                                                error_message=result.error_message,
                                                payer=check_data.payer
                                            )
                                            logger.info(f"  ✓ Sent check processing failure alert email")
                                        except Exception as e:
                                            logger.error(f"  ! Failed to send failure alert: {e}")

                                except Exception as e:
                                    logger.error(f"  ✗ Error processing check {pdf_attachment.filename}: {e}", exc_info=True)
                                    checks_failed += 1
                                    continue

                            # Mark email as processed
                            status = "success" if checks_processed > 0 else "failed"
                            error_msg = None if checks_processed > 0 else f"Failed to process {checks_failed} check(s)"

                            database.mark_processed(
                                email_id=email_data.email_id,
                                claim_number=f"{checks_processed} check(s)",
                                sender=email_data.sender,
                                subject=email_data.subject,
                                received_timestamp=email_data.timestamp,
                                status=status,
                                error_message=error_msg
                            )

                            if checks_processed > 0:
                                email.mark_as_read(email_data.email_id)
                                processed_count += 1
                            else:
                                failed_count += 1

                            logger.info(f"\n  Check processing summary: {checks_processed} succeeded, {checks_failed} failed")

                        elif is_contract:
                            # Process as contract (create new claim)
                            logger.info("Processing as CONTRACT email...")

                            contract_feature = crm.get_feature('contract_addition')
                            if not contract_feature:
                                logger.warning("Contract addition feature not enabled, skipping")
                                continue

                            # Parse contract PDF
                            if not email_data.attachments:
                                logger.warning("Contract email has no attachments, skipping")
                                continue

                            pdf_attachment = next((att for att in email_data.attachments
                                                 if att.filename.lower().endswith('.pdf')), None)
                            if not pdf_attachment:
                                logger.warning("No PDF attachment found in contract email")
                                continue

                            client_data = contract_parser.parse_contract(pdf_attachment.file_path)

                            # Create claim
                            result = contract_feature.process(client_data)

                            if result.success:
                                logger.info(f"✓ Created claim for {result.client_name}")
                                logger.info(f"✓ Claim URL: {result.claim_url}")

                                database.mark_processed(
                                    email_id=email_data.email_id,
                                    claim_number=client_data.claim_number or "N/A",
                                    sender=email_data.sender,
                                    subject=email_data.subject,
                                    received_timestamp=email_data.timestamp,
                                    status="success"
                                )
                                email.mark_as_read(email_data.email_id)
                                metrics.record_claim_created(success=True)
                                processed_count += 1

                                # Clean up: Delete contract PDF after successful claim creation
                                try:
                                    from pathlib import Path
                                    pdf_path = Path(pdf_attachment.file_path) if isinstance(pdf_attachment.file_path, str) else pdf_attachment.file_path
                                    pdf_path.unlink()
                                    logger.info(f"✓ Deleted contract PDF: {pdf_attachment.filename}")
                                except Exception as e:
                                    logger.warning(f"! Failed to delete contract PDF: {e}")
                            else:
                                logger.error(f"✗ Failed to create claim: {result.error_message}")
                                database.mark_processed(
                                    email_id=email_data.email_id,
                                    claim_number=client_data.claim_number or "N/A",
                                    sender=email_data.sender,
                                    subject=email_data.subject,
                                    received_timestamp=email_data.timestamp,
                                    status="failed",
                                    error_message=result.error_message
                                )
                                metrics.record_claim_created(success=False)
                                failed_count += 1

                        else:
                            # Process as regular email (post note)
                            logger.info("Processing as REGULAR email...")

                            if not email_data.claim_number:
                                logger.warning("No claim number found in email, skipping")
                                continue

                            comments_feature = crm.get_feature('comments')
                            if not comments_feature:
                                logger.warning("Comments feature not enabled, skipping")
                                continue

                            # Summarize email
                            summary = summarizer.summarize_email(email_data)
                            logger.info(f"  Summary title: {summary.title}")

                            # Post note (and optionally upload attachments)
                            result = comments_feature.process(email_data, summary)

                            if result.success:
                                logger.info(f"✓ Posted note to claim {email_data.claim_number}")

                                database.mark_processed(
                                    email_id=email_data.email_id,
                                    claim_number=email_data.claim_number,
                                    sender=email_data.sender,
                                    subject=email_data.subject,
                                    received_timestamp=email_data.timestamp,
                                    status="success"
                                )
                                email.mark_as_read(email_data.email_id)
                                metrics.record_note_posted(success=True)
                                processed_count += 1
                            else:
                                logger.error(f"✗ Failed to post note: {result.error_message}")
                                database.mark_processed(
                                    email_id=email_data.email_id,
                                    claim_number=email_data.claim_number,
                                    sender=email_data.sender,
                                    subject=email_data.subject,
                                    received_timestamp=email_data.timestamp,
                                    status="failed",
                                    error_message=result.error_message
                                )
                                metrics.record_note_posted(success=False)
                                failed_count += 1

                        logger.info("="*80)

                    except Exception as e:
                        logger.error(f"Unexpected error processing email: {e}", exc_info=True)
                        failed_count += 1
                        continue

                # Summary
                logger.info("="*80)
                logger.info("PROCESSING COMPLETE")
                logger.info(f"Processed: {processed_count}")
                logger.info(f"Failed: {failed_count}")
                logger.info(f"Total: {len(emails)}")
                logger.info("="*80)

                health.record_check_success(emails_processed=processed_count)
                ping_healthchecks()  # Success ping
                return 0

    except Exception as e:
        error_message = str(e)
        error_traceback = traceback.format_exc()

        logger.error(f"Fatal error: {error_message}", exc_info=True)
        health.record_check_failure(error_message)

        # Send notifications
        ping_healthchecks("/fail")
        send_failure_notification(error_message, error_traceback)

        return 1


if __name__ == "__main__":
    sys.exit(main())
