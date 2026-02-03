#!/usr/bin/env python3
"""
Script to reset emails that were incorrectly marked as 'success' but actually failed.
Run this on the production server after deploying the fix.

This will:
1. Find emails marked as 'success' with 0% actual success rate (failed attempts)
2. Mark them as 'pending' in the database
3. Mark them as UNREAD in the email inbox
4. So they can be reprocessed with the fixed code
"""
import sys
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent / "src"))

from email_monitor import EmailMonitor
from config import Config

def reset_failed_emails(days_back=7):
    """
    Reset emails that failed but were marked as success.

    Args:
        days_back: How many days back to check (default 7)
    """
    db_path = "email_processing.db"

    # Connect to database
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print(f"Checking emails from the last {days_back} days...\n")

    # Find emails marked as 'success' in the last N days
    cutoff_date = datetime.now() - timedelta(days=days_back)
    cursor.execute("""
        SELECT email_id, claim_number, sender, subject, received_at, status
        FROM emails
        WHERE status = 'success'
        AND received_at >= ?
        ORDER BY received_at DESC
    """, (cutoff_date.isoformat(),))

    success_emails = cursor.fetchall()
    print(f"Found {len(success_emails)} emails marked as 'success' in the last {days_back} days")

    if not success_emails:
        print("No emails to reset. Exiting.")
        return

    # Check which ones actually failed (have failed processing attempts)
    emails_to_reset = []

    for email in success_emails:
        cursor.execute("""
            SELECT attempt_type, success, error_message, attempted_at
            FROM processing_attempts
            WHERE email_id = ?
            ORDER BY attempted_at DESC
        """, (email['email_id'],))

        attempts = cursor.fetchall()

        # Check if all attempts failed
        if attempts and all(not attempt['success'] for attempt in attempts):
            emails_to_reset.append(email)
            print(f"\n❌ FOUND FAILED EMAIL (marked as success incorrectly):")
            print(f"   Email ID: {email['email_id']}")
            print(f"   Claim #: {email['claim_number']}")
            print(f"   From: {email['sender']}")
            print(f"   Subject: {email['subject'][:60]}...")
            print(f"   Received: {email['received_at']}")
            print(f"   Failed attempts:")
            for attempt in attempts:
                print(f"     - {attempt['attempt_type']}: {attempt['error_message']}")

    if not emails_to_reset:
        print("\n✓ All 'success' emails actually succeeded. Nothing to reset.")
        return

    print(f"\n{'='*80}")
    print(f"Found {len(emails_to_reset)} emails that failed but were marked as success")
    print(f"{'='*80}")

    # Ask for confirmation
    response = input(f"\nReset these {len(emails_to_reset)} emails to be reprocessed? (yes/no): ")
    if response.lower() != 'yes':
        print("Aborted.")
        return

    # Reset emails in database
    print("\nResetting emails in database...")
    for email in emails_to_reset:
        cursor.execute("""
            UPDATE emails
            SET status = 'pending', processed_at = NULL
            WHERE email_id = ?
        """, (email['email_id'],))
        print(f"  ✓ Reset email {email['email_id']} to 'pending'")

    conn.commit()

    # Mark emails as UNREAD in inbox
    print("\nMarking emails as UNREAD in inbox...")
    try:
        with EmailMonitor() as monitor:
            for email in emails_to_reset:
                try:
                    # Search for email by ID
                    monitor.mail.store(str(email['email_id']).encode(), '-FLAGS', '\\Seen')
                    print(f"  ✓ Marked email {email['email_id']} as UNREAD")
                except Exception as e:
                    print(f"  ⚠️  Could not mark email {email['email_id']} as unread: {e}")
                    print(f"     (You may need to manually mark it as unread in the inbox)")
    except Exception as e:
        print(f"\n⚠️  Could not connect to email inbox: {e}")
        print("You'll need to manually mark these emails as UNREAD in the inbox.")

    conn.close()

    print(f"\n{'='*80}")
    print(f"✓ Reset {len(emails_to_reset)} emails")
    print(f"{'='*80}")
    print("\nThese emails will be reprocessed on the next monitor daemon check.")
    print("Make sure you've deployed the fix before running the daemon!")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Reset failed emails for reprocessing")
    parser.add_argument('--days', type=int, default=7, help='Number of days back to check (default: 7)')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be reset without actually doing it')

    args = parser.parse_args()

    if args.dry_run:
        print("DRY RUN MODE - No changes will be made\n")

    reset_failed_emails(args.days)
