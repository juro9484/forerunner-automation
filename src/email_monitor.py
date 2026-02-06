"""
Email monitoring module for Forerunner Claims Automation.
Monitors email inbox for messages containing claim numbers and extracts relevant data.
"""

import imaplib
import email
from email.message import Message
import re
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from email.header import decode_header
from email.utils import parsedate_to_datetime
import html2text

from config import Config
from email_database import EmailDatabase
from oauth_helper import OAuthHelper
from attachment_handler import AttachmentHandler


@dataclass
class EmailData:
    """
    Structured data container for email information.

    Attributes:
        claim_number: Extracted claim number from subject line (None for new contracts)
        email_content: Parsed email body content (plain text)
        sender: Email address of sender (From field)
        recipient: Email address of recipient (To field)
        subject: Original email subject
        timestamp: When the email was received
        email_id: Unique identifier for the email message
        attachments: List of AttachmentData objects (empty list if none)
    """

    email_content: str
    sender: str
    recipient: str
    subject: str
    timestamp: datetime
    email_id: str
    claim_number: Optional[str] = None  # None for new contract emails
    attachments: list = None  # Will be populated by attachment handler

    def __post_init__(self):
        if self.attachments is None:
            self.attachments = []


class EmailMonitorError(Exception):
    """Base exception for email monitoring errors."""

    pass


class EmailConnectionError(EmailMonitorError):
    """Raised when connection to email server fails."""

    pass


class EmailAuthenticationError(EmailMonitorError):
    """Raised when authentication fails."""

    pass


class EmailMonitor:
    """
    Monitors an email inbox for messages containing claim numbers.
    Extracts and structures data for downstream processing.
    """

    def __init__(
        self,
        email_user: Optional[str] = None,
        email_pass: Optional[str] = None,
        imap_server: Optional[str] = None,
        imap_port: Optional[int] = None,
        use_database: bool = True,
    ):
        """
        Initialize the email monitor.

        Args:
            email_user: Email address to monitor (defaults to Config.BOT_EMAIL_USER)
            email_pass: Email password (defaults to Config.BOT_EMAIL_PASS)
            imap_server: IMAP server address (defaults to Config.BOT_EMAIL_IMAP_SERVER)
            imap_port: IMAP port (defaults to Config.BOT_EMAIL_IMAP_PORT)
            use_database: Enable database for duplicate detection (default: True)
        """
        self.email_user = email_user or Config.BOT_EMAIL_USER
        self.email_pass = email_pass or Config.BOT_EMAIL_PASS
        self.imap_server = imap_server or Config.BOT_EMAIL_IMAP_SERVER
        self.imap_port = imap_port or Config.BOT_EMAIL_IMAP_PORT
        self.claim_pattern = re.compile(Config.CLAIM_NUMBER_PATTERN)
        self.imap_connection: Optional[imaplib.IMAP4_SSL] = None
        self.logger = logging.getLogger(__name__)

        # Database for tracking processed emails
        self.db = EmailDatabase() if use_database else None

        # Attachment handler
        self.attachment_handler = AttachmentHandler()

        # HTML to text converter
        self.html_converter = html2text.HTML2Text()
        self.html_converter.ignore_links = False
        self.html_converter.body_width = 0  # Don't wrap text

    def connect(self) -> None:
        """
        Establish connection to IMAP server and authenticate.

        Raises:
            EmailConnectionError: If connection fails
            EmailAuthenticationError: If authentication fails
        """
        try:
            self.logger.info(f"Connecting to IMAP server: {self.imap_server}:{self.imap_port}")
            self.imap_connection = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            self.logger.info("IMAP connection established")

            # Authenticate - OAuth or basic auth
            if Config.USE_OAUTH:
                self.logger.info(f"Authenticating with OAuth as {self.email_user}")
                oauth_helper = OAuthHelper()
                access_token = oauth_helper.get_access_token()
                auth_string = oauth_helper.generate_oauth_string(self.email_user, access_token)

                # Use XOAUTH2 authentication
                # The authenticate method callback should return bytes
                self.imap_connection.authenticate("XOAUTH2", lambda x: auth_string)
                self.logger.info("OAuth authentication successful")
            else:
                self.logger.info(f"Authenticating with password as {self.email_user}")
                self.imap_connection.login(self.email_user, self.email_pass)
                self.logger.info("Authentication successful")

        except imaplib.IMAP4.error as e:
            error_msg = f"IMAP authentication failed: {str(e)}"
            self.logger.error(error_msg)
            raise EmailAuthenticationError(error_msg) from e
        except Exception as e:
            error_msg = f"Failed to connect to email server: {str(e)}"
            self.logger.error(error_msg)
            raise EmailConnectionError(error_msg) from e

    def disconnect(self) -> None:
        """Safely disconnect from IMAP server."""
        if self.imap_connection:
            try:
                self.imap_connection.close()
                self.imap_connection.logout()
                self.logger.info("Disconnected from IMAP server")
            except Exception as e:
                self.logger.warning(f"Error during disconnect: {str(e)}")
            finally:
                self.imap_connection = None

    def __enter__(self):
        """Context manager entry - establish connection."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensure cleanup."""
        self.disconnect()
        return False

    def _decode_header_value(self, header_value: str) -> str:
        """
        Decode email header value handling various encodings.

        Args:
            header_value: Raw header value

        Returns:
            Decoded string
        """
        if not header_value:
            return ""

        decoded_parts = []
        for part, encoding in decode_header(header_value):
            if isinstance(part, bytes):
                decoded_parts.append(part.decode(encoding or "utf-8", errors="replace"))
            else:
                decoded_parts.append(part)

        return "".join(decoded_parts)

    def _extract_claim_number(self, subject: str) -> Optional[str]:
        """
        Extract claim number from email subject line.

        Args:
            subject: Email subject line

        Returns:
            Claim number if found (normalized to uppercase), None otherwise
        """
        match = self.claim_pattern.search(subject)
        if match:
            # Normalize to uppercase for consistency
            claim_number = match.group(1).upper()

            # Reject all-letter "claim numbers" like "CLAIM", "CONTRACT", etc.
            # Real claim numbers always have at least one digit
            if not any(char.isdigit() for char in claim_number):
                self.logger.debug(f"Rejected all-letter claim number: {claim_number}")
                return None

            self.logger.debug(f"Extracted claim number: {claim_number}")
            return claim_number
        return None

    def _get_email_body(self, message: Message) -> str:
        """
        Extract and parse email body content.
        Handles both plain text and HTML emails.

        Args:
            message: Email message object

        Returns:
            Parsed email body as plain text
        """
        body_text = ""

        try:
            if message.is_multipart():
                # Process multipart message
                for part in message.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition", ""))

                    # Skip attachments
                    if "attachment" in content_disposition:
                        continue

                    if content_type == "text/plain":
                        # Plain text content
                        payload = part.get_payload(decode=True)
                        if payload:
                            charset = part.get_content_charset() or "utf-8"
                            body_text = payload.decode(charset, errors="replace")
                            break  # Prefer plain text, so break if found

                    elif content_type == "text/html" and not body_text:
                        # HTML content - convert to plain text
                        payload = part.get_payload(decode=True)
                        if payload:
                            charset = part.get_content_charset() or "utf-8"
                            html_content = payload.decode(charset, errors="replace")
                            body_text = self.html_converter.handle(html_content)

            else:
                # Simple non-multipart message
                content_type = message.get_content_type()
                payload = message.get_payload(decode=True)

                if payload:
                    charset = message.get_content_charset() or "utf-8"
                    decoded_payload = payload.decode(charset, errors="replace")

                    if content_type == "text/html":
                        body_text = self.html_converter.handle(decoded_payload)
                    else:
                        body_text = decoded_payload

        except Exception as e:
            self.logger.error(f"Error parsing email body: {str(e)}")
            body_text = "[Error: Could not parse email body]"

        return body_text.strip()

    def _parse_email(self, email_id: str, message_data: bytes) -> Optional[EmailData]:
        """
        Parse raw email message data into structured EmailData.

        Args:
            email_id: Unique email identifier
            message_data: Raw email message bytes

        Returns:
            EmailData object if claim number found, None otherwise
        """
        try:
            # Parse email message
            message = email.message_from_bytes(message_data)

            # Extract and decode headers
            subject = self._decode_header_value(message.get("Subject", ""))
            sender = self._decode_header_value(message.get("From", ""))
            recipient = self._decode_header_value(message.get("To", ""))
            date_str = message.get("Date", "")

            # Parse timestamp
            try:
                timestamp = parsedate_to_datetime(date_str)
            except Exception:
                timestamp = datetime.now()

            # Extract claim number from subject
            claim_number = self._extract_claim_number(subject)

            # Check if this is a contract email (new client)
            is_contract_email = "contract" in subject.lower()

            # Skip if no claim number AND not a contract email
            if not claim_number and not is_contract_email:
                self.logger.debug(f"No claim number or contract keyword in subject: {subject}")
                return None

            # Extract email body
            email_content = self._get_email_body(message)

            # Extract attachments
            attachments = self.attachment_handler.extract_attachments(message, email_id)
            if attachments:
                self.logger.info(f"Found {len(attachments)} attachment(s)")

            # Create structured data
            email_data = EmailData(
                claim_number=claim_number,  # Will be None for contract emails
                email_content=email_content,
                sender=sender,
                recipient=recipient,
                subject=subject,
                timestamp=timestamp,
                email_id=email_id,
                attachments=attachments,
            )

            if is_contract_email:
                self.logger.info(
                    f"Parsed CONTRACT email from {sender} (ID: {email_id})"
                )
            else:
                self.logger.info(
                    f"Parsed email from {sender} with claim #{claim_number} (ID: {email_id})"
                )
            return email_data

        except Exception as e:
            self.logger.error(f"Error parsing email {email_id}: {str(e)}")
            return None

    def fetch_unread_emails(self) -> List[EmailData]:
        """
        Fetch all unread emails containing claim numbers.

        Returns:
            List of EmailData objects for emails with claim numbers

        Raises:
            EmailMonitorError: If not connected or fetch fails
        """
        if not self.imap_connection:
            raise EmailMonitorError("Not connected to email server. Call connect() first.")

        try:
            # Select inbox
            self.imap_connection.select("INBOX")
            self.logger.info("Selected INBOX")

            # Search for unread emails
            status, message_ids = self.imap_connection.search(None, "UNSEEN")

            if status != "OK":
                raise EmailMonitorError(f"Failed to search emails: {status}")

            # Get list of email IDs
            email_ids = message_ids[0].split()

            if not email_ids:
                self.logger.info("No unread emails found")
                return []

            self.logger.info(f"Found {len(email_ids)} unread email(s)")

            # Process each email
            parsed_emails = []
            for email_id in email_ids:
                try:
                    email_id_str = email_id.decode()

                    # Check if already processed (skip if database enabled)
                    if self.db and self.db.is_processed(email_id_str):
                        self.logger.debug(f"Email {email_id_str} already processed, skipping")
                        continue

                    # Fetch email data
                    status, msg_data = self.imap_connection.fetch(email_id, "(RFC822)")

                    if status != "OK":
                        self.logger.warning(f"Failed to fetch email {email_id}: {status}")
                        continue

                    # Parse email
                    email_data = self._parse_email(email_id_str, msg_data[0][1])

                    if email_data:
                        parsed_emails.append(email_data)

                except Exception as e:
                    self.logger.error(f"Error processing email {email_id}: {str(e)}")
                    continue

            self.logger.info(f"Successfully parsed {len(parsed_emails)} email(s) with claim numbers")
            return parsed_emails

        except Exception as e:
            error_msg = f"Error fetching emails: {str(e)}"
            self.logger.error(error_msg)
            raise EmailMonitorError(error_msg) from e

    def mark_as_read(self, email_id: str) -> bool:
        """
        Mark an email as read.

        Args:
            email_id: Unique email identifier

        Returns:
            True if successful, False otherwise
        """
        if not self.imap_connection:
            self.logger.error("Not connected to email server")
            return False

        try:
            self.imap_connection.select("INBOX")
            status, _ = self.imap_connection.store(email_id.encode(), "+FLAGS", "\\Seen")

            if status == "OK":
                self.logger.info(f"Marked email {email_id} as read")
                return True
            else:
                self.logger.error(f"Failed to mark email {email_id} as read: {status}")
                return False

        except Exception as e:
            self.logger.error(f"Error marking email as read: {str(e)}")
            return False

    def mark_email_processed(
        self,
        email_data: EmailData,
        status: str = "success",
        error_message: Optional[str] = None,
    ) -> bool:
        """
        Mark an email as processed in the database.

        Args:
            email_data: EmailData object to mark as processed
            status: Processing status ('success' or 'failed')
            error_message: Optional error message if failed

        Returns:
            True if marked successfully, False otherwise
        """
        if not self.db:
            self.logger.debug("Database not enabled, skipping mark_processed")
            return True

        try:
            self.db.mark_processed(
                email_id=email_data.email_id,
                claim_number=email_data.claim_number,
                sender=email_data.sender,
                subject=email_data.subject,
                received_timestamp=email_data.timestamp,
                status=status,
                error_message=error_message,
            )
            return True
        except Exception as e:
            self.logger.error(f"Error marking email as processed in database: {e}")
            return False

    def mark_email_fully_processed(
        self,
        email_data: EmailData,
        status: str = "success",
        error_message: Optional[str] = None,
    ) -> bool:
        """
        ATOMIC operation: Mark email as processed in DB AND mark as read in IMAP.
        If either operation fails, rolls back both to maintain consistency.

        Args:
            email_data: EmailData object to mark as processed
            status: Processing status ('success' or 'failed')
            error_message: Optional error message if failed

        Returns:
            True if both operations succeeded, False otherwise
        """
        if not self.db:
            # If no database, just mark as read
            return self.mark_as_read(email_data.email_id)

        try:
            # STEP 1: Mark in database
            db_success = self.mark_email_processed(email_data, status, error_message)

            if not db_success:
                raise Exception("Database write failed")

            # STEP 2: Mark as read in email (only for successful processing)
            if status == "success":
                read_success = self.mark_as_read(email_data.email_id)

                if not read_success:
                    # CRITICAL: Database says processed but email still unread
                    # ROLLBACK: Remove from database to force reprocessing
                    self.logger.error(
                        f"❌ CONSISTENCY ERROR: Email {email_data.email_id} marked in DB but failed to mark as read"
                    )
                    self.db.delete_processed(email_data.email_id)
                    raise Exception("Failed to mark as read, rolled back database entry")

            self.logger.info(f"✓ Email {email_data.email_id} fully processed (DB + IMAP)")
            return True

        except Exception as e:
            self.logger.error(f"❌ ATOMIC PROCESSING FAILED: {e}")
            # This error will be caught by caller who should send notification
            return False

    def process_emails(self) -> List[EmailData]:
        """
        High-level method to fetch and process unread emails.
        This is the main entry point for email monitoring.

        Returns:
            List of EmailData objects ready for downstream processing
        """
        self.logger.info("Starting email processing")

        try:
            emails = self.fetch_unread_emails()
            self.logger.info(f"Retrieved {len(emails)} email(s) for processing")
            return emails

        except Exception as e:
            self.logger.error(f"Error during email processing: {str(e)}")
            raise


# Example usage for testing
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Test the email monitor
    try:
        with EmailMonitor() as monitor:
            emails = monitor.process_emails()

            for email_data in emails:
                print(f"\n{'=' * 80}")
                print(f"Claim Number: {email_data.claim_number}")
                print(f"From: {email_data.sender}")
                print(f"Subject: {email_data.subject}")
                print(f"Timestamp: {email_data.timestamp}")
                print(f"Content Preview: {email_data.email_content[:200]}...")

    except EmailMonitorError as e:
        logging.error(f"Email monitoring failed: {e}")
