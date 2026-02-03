#!/usr/bin/env python3
"""
Quick test script to verify email notifications are working.
"""

import sys
from pathlib import Path
from datetime import datetime

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from config import Config
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def send_test_notification():
    """Send a test notification email."""
    try:
        # Notification recipients
        notification_emails = [
            "juan@roaksystems.com",
            "juanrod2000@gmail.com",
            "leifohovda@gmail.com",
            "leif@roaksystems.com",
            "support@roaksystems.com"
        ]
        recipients = ", ".join(notification_emails)

        # Create email
        msg = MIMEMultipart()
        msg['From'] = Config.BOT_EMAIL_USER
        msg['To'] = recipients
        msg['Subject'] = "🚨 Forerunner Automation Alert: Test Notification"

        # Build email body
        body = f"""
Forerunner Claims Automation Alert
{'='*60}

ERROR: Test Notification

Details:
This is a test notification to verify the email alert system is working correctly.

Email Context:
- From: test@example.com
- Subject: Test Email #12345
- Claim #: 12345
- Email ID: TEST-001

Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Please check the logs for more details.

{'='*60}
Forerunner Claims Automation System
"""

        msg.attach(MIMEText(body, 'plain'))

        # Send email
        print("Connecting to SMTP server...")
        # Office 365 uses smtp.office365.com on port 587 with STARTTLS
        smtp_server = "smtp.office365.com"
        smtp_port = 587
        print(f"SMTP Server: {smtp_server}:{smtp_port}")

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            print("Starting TLS...")
            server.starttls()
            print("Logging in...")
            server.login(Config.BOT_EMAIL_USER, Config.BOT_EMAIL_PASS)
            print("Sending message...")
            server.send_message(msg)

        print(f"\n✓ Test notification sent successfully to:")
        for email in notification_emails:
            print(f"  - {email}")

    except Exception as e:
        print(f"\n✗ Failed to send test notification: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("="*60)
    print("Forerunner Automation - Email Notification Test")
    print("="*60)
    print()
    send_test_notification()
    print()
    print("="*60)
