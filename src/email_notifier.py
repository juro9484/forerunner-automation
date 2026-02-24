"""
Email notification utility for sending alerts and summaries.
Handles SMTP connection and email formatting.
"""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional, List


class EmailNotifier:
    """
    Sends email notifications for alerts and summaries.
    Uses SMTP (Gmail by default).
    """

    def __init__(
        self,
        smtp_server: str = "smtp.gmail.com",
        smtp_port: int = 587,
        from_email: str = None,
        from_password: str = None,
        to_emails: List[str] = None
    ):
        """
        Initialize email notifier.

        Args:
            smtp_server: SMTP server address
            smtp_port: SMTP port (587 for TLS)
            from_email: Sender email address
            from_password: Sender email password/app password
            to_emails: List of recipient email addresses
        """
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.from_email = from_email
        self.from_password = from_password
        self.to_emails = to_emails or []
        self.logger = logging.getLogger(__name__)

    def send_email(
        self,
        subject: str,
        body_html: str,
        body_text: Optional[str] = None
    ) -> bool:
        """
        Send an email notification to all recipients.

        Args:
            subject: Email subject line
            body_html: HTML email body
            body_text: Plain text fallback (optional)

        Returns:
            True if sent successfully, False otherwise
        """
        if not all([self.from_email, self.from_password, self.to_emails]):
            self.logger.error("Email credentials not configured")
            return False

        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = ', '.join(self.to_emails)

            # Add text and HTML parts
            if body_text:
                part1 = MIMEText(body_text, 'plain')
                msg.attach(part1)

            part2 = MIMEText(body_html, 'html')
            msg.attach(part2)

            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.from_email, self.from_password)
                server.send_message(msg)

            self.logger.info(f"Email sent to {len(self.to_emails)} recipients: {subject}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to send email: {e}")
            return False

    def send_failure_alert(
        self,
        client_id: str,
        error_message: str,
        error_details: Optional[str] = None
    ) -> bool:
        """
        Send immediate failure alert email.

        Args:
            client_id: Client identifier
            error_message: Brief error description
            error_details: Full error traceback (optional)

        Returns:
            True if sent successfully
        """
        subject = f"🚨 ALERT: {client_id} Service Failure"

        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        details_html = f'<h3>Details:</h3><pre style="background: #f5f5f5; padding: 10px; overflow-x: auto;">{error_details}</pre>' if error_details else ''
        details_text = f'Details:\n{error_details}' if error_details else ''

        body_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2 style="color: #d32f2f;">⚠️ Service Failure Alert</h2>
            <p><strong>Client:</strong> {client_id}</p>
            <p><strong>Time:</strong> {timestamp}</p>
            <p><strong>Error:</strong> {error_message}</p>

            {details_html}

            <hr>
            <p style="color: #666; font-size: 12px;">
                Check logs: <code>tail -50 logs/{client_id}.log</code><br>
                Service status: <code>sudo systemctl status forerunner-monitor</code>
            </p>
        </body>
        </html>
        """

        body_text = f"""
SERVICE FAILURE ALERT

Client: {client_id}
Time: {timestamp}
Error: {error_message}

{details_text}

Check logs: tail -50 logs/{client_id}.log
Service status: sudo systemctl status forerunner-monitor
        """

        return self.send_email(subject, body_html, body_text)

    def send_success_alert(
        self,
        client_id: str,
        message: str,
        details: Optional[str] = None
    ) -> bool:
        """
        Send success/startup notification email.

        Args:
            client_id: Client identifier
            message: Success message
            details: Additional details (optional)

        Returns:
            True if sent successfully
        """
        subject = f"✅ {client_id} - {message}"

        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        details_html = f'<p style="background: #e8f5e9; padding: 10px; border-radius: 5px;">{details}</p>' if details else ''
        details_text = f'\n{details}' if details else ''

        body_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2 style="color: #4caf50;">✅ Success Notification</h2>
            <p><strong>Client:</strong> {client_id}</p>
            <p><strong>Time:</strong> {timestamp}</p>
            <p><strong>Message:</strong> {message}</p>

            {details_html}

            <hr>
            <p style="color: #666; font-size: 12px;">
                View logs: <code>tail -50 logs/{client_id}.log</code><br>
                Service status: <code>sudo systemctl status forerunner-monitor</code>
            </p>
        </body>
        </html>
        """

        body_text = f"""
SUCCESS NOTIFICATION

Client: {client_id}
Time: {timestamp}
Message: {message}
{details_text}

View logs: tail -50 logs/{client_id}.log
Service status: sudo systemctl status forerunner-monitor
        """

        return self.send_email(subject, body_html, body_text)

    def send_hourly_summary(
        self,
        client_id: str,
        emails_processed: int,
        emails_failed: int,
        notes_posted: int,
        claims_created: int,
        period_start: str,
        period_end: str
    ) -> bool:
        """
        Send hourly summary email.

        Args:
            client_id: Client identifier
            emails_processed: Number of emails processed successfully
            emails_failed: Number of emails that failed
            notes_posted: Number of notes posted to claims
            claims_created: Number of new claims created
            period_start: Start time of period
            period_end: End time of period

        Returns:
            True if sent successfully
        """
        total_emails = emails_processed + emails_failed
        success_rate = (emails_processed / total_emails * 100) if total_emails > 0 else 0

        # Determine status emoji
        if emails_failed == 0:
            status_emoji = "✅"
            status_color = "#4caf50"
        elif emails_failed < emails_processed:
            status_emoji = "⚠️"
            status_color = "#ff9800"
        else:
            status_emoji = "❌"
            status_color = "#f44336"

        subject = f"{status_emoji} {client_id} - Hourly Summary ({success_rate:.0f}% success)"

        body_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2 style="color: {status_color};">{status_emoji} Hourly Summary Report</h2>

            <div style="background: #f5f5f5; padding: 15px; border-radius: 5px; margin: 10px 0;">
                <p><strong>Client:</strong> {client_id}</p>
                <p><strong>Period:</strong> {period_start} - {period_end}</p>
            </div>

            <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                <tr style="background: #e3f2fd;">
                    <th style="padding: 10px; text-align: left; border: 1px solid #ddd;">Metric</th>
                    <th style="padding: 10px; text-align: right; border: 1px solid #ddd;">Count</th>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;">Emails Processed</td>
                    <td style="padding: 10px; text-align: right; border: 1px solid #ddd; color: #4caf50; font-weight: bold;">{emails_processed}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;">Emails Failed</td>
                    <td style="padding: 10px; text-align: right; border: 1px solid #ddd; color: #f44336; font-weight: bold;">{emails_failed}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;">Notes Posted</td>
                    <td style="padding: 10px; text-align: right; border: 1px solid #ddd;">{notes_posted}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;">Claims Created</td>
                    <td style="padding: 10px; text-align: right; border: 1px solid #ddd;">{claims_created}</td>
                </tr>
                <tr style="background: #e8f5e9;">
                    <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">Success Rate</td>
                    <td style="padding: 10px; text-align: right; border: 1px solid #ddd; font-weight: bold;">{success_rate:.1f}%</td>
                </tr>
            </table>

            <hr>
            <p style="color: #666; font-size: 12px;">
                View logs: <code>tail -50 logs/{client_id}.log</code><br>
                Check metrics: <code>cat logs/metrics.txt</code>
            </p>
        </body>
        </html>
        """

        body_text = f"""
HOURLY SUMMARY REPORT

Client: {client_id}
Period: {period_start} - {period_end}

Metrics:
---------
Emails Processed: {emails_processed}
Emails Failed: {emails_failed}
Notes Posted: {notes_posted}
Claims Created: {claims_created}
Success Rate: {success_rate:.1f}%

View logs: tail -50 logs/{client_id}.log
Check metrics: cat logs/metrics.txt
        """

        return self.send_email(subject, body_html, body_text)
