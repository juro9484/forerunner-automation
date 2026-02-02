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
from claim_titan_bot import ClaimTitanBot, ClaimTitanError, ClaimCreationResult
from contract_parser import ContractParser, ContractParserError
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


def send_failure_notification(subject: str, error_message: str, email_data=None):
    """
    Send email notification when processing fails.

    Args:
        subject: Notification subject
        error_message: Error details
        email_data: Optional email data for context
    """
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    try:
        # Notification recipients
        notification_emails = ["juan@roaksystems.com", "juanrod2000@gmail.com"]
        recipients = ", ".join(notification_emails)

        # Create email
        msg = MIMEMultipart()
        msg['From'] = Config.BOT_EMAIL_USER
        msg['To'] = recipients
        msg['Subject'] = f"🚨 Forerunner Automation Alert: {subject}"

        # Build email body
        body = f"""
Forerunner Claims Automation Alert
{'='*60}

ERROR: {subject}

Details:
{error_message}

"""

        if email_data:
            body += f"""
Email Context:
- From: {email_data.sender}
- Subject: {email_data.subject}
- Claim #: {email_data.claim_number if hasattr(email_data, 'claim_number') else 'N/A'}
- Email ID: {email_data.email_id}

"""

        body += f"""
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Please check the logs for more details.

{'='*60}
Forerunner Claims Automation System
"""

        msg.attach(MIMEText(body, 'plain'))

        # Send email (Office 365 uses port 587 with STARTTLS)
        with smtplib.SMTP("smtp.office365.com", 587) as server:
            server.starttls()
            server.login(Config.BOT_EMAIL_USER, Config.BOT_EMAIL_PASS)
            server.send_message(msg)

        logger.info(f"✓ Sent failure notification to {recipients}")

    except Exception as e:
        logger.error(f"Failed to send notification email: {e}")


def extract_contact_info_from_email(email_content: str) -> dict:
    """
    Extract contact information from email body.
    Looks for phone (9+ digits), email (@ sign), and name.
    Handles various formats like:
    - "Contact info: Name, email, phone"
    - "Contact:\nName\nemail\nphone"
    - "claim contact: Name / email / phone"

    Args:
        email_content: Email body text

    Returns:
        Dict with 'phone', 'email', 'first_name', 'last_name' (or None if not found)
    """
    import re

    result = {
        'phone': None,
        'email': None,
        'first_name': None,
        'last_name': None
    }

    # Look for contact section with flexible matching
    contact_patterns = [
        r'(?:claim\s*)?contact\s*(?:info)?[:\s]+(.+?)(?:\n\n|\Z)',  # "contact:" or "claim contact:" followed by content
        r'(?:claim\s*)?contact[:\s]+(.+?)(?:\n\n|\Z)',  # More flexible
    ]

    contact_text = None
    for pattern in contact_patterns:
        match = re.search(pattern, email_content, re.IGNORECASE | re.DOTALL)
        if match:
            contact_text = match.group(1).strip()
            break

    # If no contact section found, search entire email
    if not contact_text:
        contact_text = email_content

    # Split by common separators (newlines, commas, slashes)
    contact_lines = re.split(r'[\n,/]+', contact_text)

    # Extract phone
    phone_patterns = [
        r'\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}',  # US phone with various formats
        r'\d{10,}',  # Any sequence of 10+ digits
    ]

    for line in contact_lines:
        for pattern in phone_patterns:
            match = re.search(pattern, line)
            if match:
                phone = re.sub(r'\D', '', match.group())
                if len(phone) >= 9:
                    # Format as (XXX) XXX-XXXX if 10 digits
                    if len(phone) == 10:
                        result['phone'] = f"({phone[:3]}) {phone[3:6]}-{phone[6:]}"
                    else:
                        result['phone'] = phone
                    break
        if result['phone']:
            break

    # Extract email (line with @)
    for line in contact_lines:
        if '@' in line:
            # Extract email address
            email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', line)
            if email_match:
                result['email'] = email_match.group()
                break

    # Extract name (text line that's not phone or email)
    for line in contact_lines:
        # Skip if it's the phone or email line
        if result['phone'] and result['phone'].replace('(', '').replace(')', '').replace(' ', '').replace('-', '') in line.replace(' ', '').replace('-', ''):
            continue
        if result['email'] and result['email'] in line:
            continue

        # Check if line looks like a name (letters, spaces, maybe hyphen)
        if re.match(r'^[A-Za-z\s\-]+$', line):
            # Split into first and last name
            name_parts = line.split()
            if len(name_parts) >= 2:
                result['first_name'] = name_parts[0]
                result['last_name'] = ' '.join(name_parts[1:])
            elif len(name_parts) == 1:
                result['first_name'] = name_parts[0]
            break

    return result


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global running
    logger.info("Shutdown signal received. Stopping monitor...")
    running = False
    # Note: Browser is opened/closed per email, so no cleanup needed here


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
    logger.info(f"Contract Processing: ENABLED (detects 'contract' in subject)")
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

    # NOTE: We no longer initialize the browser at startup
    # Instead, we'll open/close it for each email to avoid Windows service issues
    logger.info("")  # Blank line for readability

    while running:
        check_count += 1
        logger.info(f"\n[Check #{check_count}] Starting email check at {datetime.now()}")

        try:
            # Connect and check emails
            with EmailMonitor() as monitor:
                emails = monitor.process_emails()

                if emails:
                    logger.info(f"✓ Found {len(emails)} new email(s)")

                    for email_data in emails:
                        # Check if this is a contract email (new client)
                        # Look for trigger words in subject line (case-insensitive)
                        subject_lower = email_data.subject.lower()
                        contract_triggers = ["contract", "new contract", "new claim", "new client", "new customer", "new policy"]
                        is_contract_email = any(trigger in subject_lower for trigger in contract_triggers)

                        if is_contract_email:
                            logger.info(f"\n  📄 NEW CLIENT EMAIL DETECTED")
                        else:
                            logger.info(f"\n  Claim #{email_data.claim_number}")

                        logger.info(f"  From: {email_data.sender}")
                        logger.info(f"  Subject: {email_data.subject}")
                        logger.info(f"  Content preview: {email_data.email_content[:100]}...")

                        # Route to appropriate workflow
                        if is_contract_email:
                            # ===== CONTRACT WORKFLOW: Parse contract and create new claim =====
                            try:
                                logger.info(f"\n  Starting CONTRACT processing workflow...")

                                # Find PDF attachment
                                pdf_attachment = None
                                for attachment in email_data.attachments:
                                    if attachment.content_type == "application/pdf" or attachment.filename.lower().endswith('.pdf'):
                                        pdf_attachment = attachment
                                        break

                                if not pdf_attachment:
                                    logger.error(f"  ✗ No PDF attachment found in contract email")
                                    monitor.mark_email_processed(email_data, status="failed", error_message="No PDF attachment")
                                    continue

                                logger.info(f"  ✓ Found PDF attachment: {pdf_attachment.filename}")

                                # Parse contract with Claude
                                logger.info(f"  Parsing contract with Claude AI...")
                                parser = ContractParser()
                                client_data = parser.parse_contract(pdf_attachment.file_path)

                                # Extract contact info from email body (takes priority over contract)
                                logger.info(f"  Extracting contact info from email body...")
                                email_contact = extract_contact_info_from_email(email_data.email_content)

                                # Override contract data with email data (email takes priority)
                                if email_contact['phone']:
                                    logger.info(f"  ✓ Phone from email: {email_contact['phone']}")
                                    client_data.phone = email_contact['phone']

                                if email_contact['email']:
                                    logger.info(f"  ✓ Email from email: {email_contact['email']}")
                                    client_data.email = email_contact['email']

                                if email_contact['first_name']:
                                    logger.info(f"  ✓ Name from email: {email_contact['first_name']} {email_contact['last_name'] or ''}")
                                    client_data.first_name = email_contact['first_name']
                                    if email_contact['last_name']:
                                        client_data.last_name = email_contact['last_name']

                                client_name = f"{client_data.first_name} {client_data.last_name or ''}".strip()
                                logger.info(f"\n  " + "="*70)
                                logger.info(f"  EXTRACTED CLIENT DATA")
                                logger.info(f"  " + "="*70)
                                logger.info(f"  Name: {client_name}")
                                logger.info(f"  Email: {client_data.email or '(not found)'}")
                                logger.info(f"  Phone: {client_data.phone or '(not found)'}")
                                logger.info(f"  Address: {client_data.street_address}, {client_data.city}, {client_data.state} {client_data.zipcode}")
                                logger.info(f"  Insurance: {client_data.insurance_company or '(not found)'}")
                                logger.info(f"  Loss Type: {client_data.loss_type or '(not found)'}")
                                logger.info(f"  Loss Date: {client_data.loss_date or '(not found)'}")
                                logger.info(f"  " + "="*70 + "\n")

                                # Create claim in Claim Titan
                                bot = None
                                try:
                                    logger.info(f"  Opening browser and logging into Claim Titan...")
                                    bot = ClaimTitanBot()
                                    bot.connect()
                                    logger.info(f"  ✓ Browser opened and logged in")

                                    logger.info(f"  Creating new claim in Claim Titan...")
                                    result = bot.create_claim(client_data)

                                    if result.success:
                                        logger.info(f"  ✓ Created claim successfully!")
                                        logger.info(f"  ✓ Claim URL: {result.claim_url}")
                                        monitor.mark_email_processed(email_data, status="success")
                                        monitor.mark_as_read(email_data.email_id)
                                        total_emails_processed += 1
                                    else:
                                        logger.error(f"  ✗ Failed to create claim: {result.error_message}")
                                        if result.screenshot_path:
                                            logger.error(f"  Screenshot: {result.screenshot_path}")
                                        monitor.mark_email_processed(email_data, status="failed", error_message=result.error_message)

                                        # Send failure notification
                                        send_failure_notification(
                                            subject="Claim Creation Failed",
                                            error_message=f"Failed to create claim for {client_name}:\n{result.error_message}\nScreenshot: {result.screenshot_path or 'N/A'}",
                                            email_data=email_data
                                        )

                                except Exception as e:
                                    logger.error(f"  ✗ Error creating claim: {e}", exc_info=True)
                                    monitor.mark_email_processed(email_data, status="failed", error_message=str(e))

                                    # Send failure notification
                                    send_failure_notification(
                                        subject="Claim Creation Error",
                                        error_message=f"Unexpected error creating claim for {client_name}:\n{str(e)}",
                                        email_data=email_data
                                    )

                                finally:
                                    if bot:
                                        bot.disconnect()
                                        logger.info(f"  ✓ Browser closed")

                            except ContractParserError as e:
                                logger.error(f"  ✗ Contract parsing failed: {e}")
                                monitor.mark_email_processed(email_data, status="failed", error_message=str(e))

                                # Send failure notification
                                send_failure_notification(
                                    subject="Contract Parsing Failed",
                                    error_message=f"Failed to parse contract PDF:\n{str(e)}",
                                    email_data=email_data
                                )

                            except Exception as e:
                                logger.error(f"  ✗ Unexpected error during contract processing: {e}", exc_info=True)
                                monitor.mark_email_processed(email_data, status="failed", error_message=str(e))

                                # Send failure notification
                                send_failure_notification(
                                    subject="Contract Processing Failed - Unexpected Error",
                                    error_message=f"Unexpected error during contract processing:\n{str(e)}",
                                    email_data=email_data
                                )

                        else:
                            # ===== EXISTING CLAIM WORKFLOW: Summarize and post note =====
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

                                # Post to Claim Titan CRM (open browser for this email only)
                                bot = None
                                try:
                                    logger.info(f"  Opening browser and logging into Claim Titan...")
                                    bot = ClaimTitanBot()
                                    bot.connect()
                                    logger.info(f"  ✓ Browser opened and logged in")

                                    logger.info(f"  Posting note to Claim Titan...")
                                    result = bot.post_note(
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

                                    # Handle attachments if any (while browser is still open)
                                    if email_data.attachments and bot:
                                        try:
                                            logger.info(f"  Processing {len(email_data.attachments)} attachment(s)...")

                                            # Upload attachments (or log in test mode)
                                            # Returns dict mapping filename -> folder_name (or "Failed" if failed)
                                            upload_results = bot.upload_attachments(
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
                                                    permanent_path = bot.attachment_handler.move_to_permanent_storage(
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

                                except ClaimTitanError as e:
                                    logger.error(f"  ✗ Claim Titan error: {e}")
                                    logger.error(f"  Note was not posted to CRM, but will continue processing")

                                    # Send failure notification
                                    send_failure_notification(
                                        subject="Note Posting Failed - Claim Titan Error",
                                        error_message=f"Failed to post note for claim #{email_data.claim_number}:\n{str(e)}",
                                        email_data=email_data
                                    )

                                except Exception as e:
                                    logger.error(f"  ✗ Unexpected error posting to Claim Titan: {e}")
                                    logger.error(f"  Note was not posted to CRM, but will continue processing")

                                    # Send failure notification
                                    send_failure_notification(
                                        subject="Note Posting Failed - Unexpected Error",
                                        error_message=f"Unexpected error posting note for claim #{email_data.claim_number}:\n{str(e)}",
                                        email_data=email_data
                                    )

                                finally:
                                    # Always close browser after posting (or if error)
                                    if bot:
                                        try:
                                            bot.disconnect()
                                            logger.info(f"  ✓ Browser closed")
                                        except Exception as e:
                                            logger.warning(f"  Error closing browser: {e}")

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

                                # Send failure notification
                                send_failure_notification(
                                    subject="Email Summarization Failed",
                                    error_message=f"Failed to generate AI summary for claim #{email_data.claim_number}:\n{str(e)}",
                                    email_data=email_data
                                )

                            except Exception as e:
                                logger.error(f"  ✗ Unexpected error during processing: {e}", exc_info=True)
                                monitor.mark_email_processed(email_data, status="failed", error_message=str(e))
                                logger.info(f"  Email marked as failed in database")

                                # Send failure notification
                                send_failure_notification(
                                    subject="Claim Processing Failed - Unexpected Error",
                                    error_message=f"Unexpected error processing claim #{email_data.claim_number}:\n{str(e)}",
                                    email_data=email_data
                                )

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

    # Note: No browser cleanup needed - opened/closed per email

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
