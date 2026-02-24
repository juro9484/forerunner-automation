#!/usr/bin/env python3
"""
One-time script to mark all existing emails as processed.
This prevents old emails from being re-processed after keyword changes.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from adapters.email.outlook.adapter import OutlookAdapter
from email_database import EmailDatabase


def main():
    """Mark all emails from last 30 days as processed."""
    print("Connecting to email and database...")

    database = EmailDatabase()

    with OutlookAdapter() as email_adapter:
        # Temporarily disable database checking in adapter to get ALL emails
        email_adapter.db = None

        print("Fetching all emails from last 30 days...")

        # Get all emails (without database filtering)
        emails = email_adapter.fetch_unread_emails()

        print(f"Found {len(emails)} email(s)")

        marked_count = 0
        skipped_count = 0

        for email_data in emails:
            # Check if already in database
            if database.is_processed(email_data.email_id):
                print(f"  Already processed: {email_data.subject[:60]}")
                skipped_count += 1
                continue

            # Mark as processed
            database.mark_processed(
                email_id=email_data.email_id,
                claim_number=email_data.claim_number or "N/A",
                sender=email_data.sender,
                subject=email_data.subject,
                received_timestamp=email_data.timestamp,
                status="skipped_bulk_mark"
            )

            print(f"  ✓ Marked as processed: {email_data.subject[:60]}")
            marked_count += 1

        print("\n" + "="*80)
        print(f"COMPLETE")
        print(f"Marked as processed: {marked_count}")
        print(f"Already processed: {skipped_count}")
        print(f"Total: {len(emails)}")
        print("="*80)


if __name__ == "__main__":
    main()
