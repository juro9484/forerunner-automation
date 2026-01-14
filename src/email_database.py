"""
Database module for tracking processed emails.
Prevents duplicate processing and maintains audit trail.
Uses SQLite - a free, file-based database with zero cost.
"""

import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from contextlib import contextmanager

from config import Config


class EmailDatabase:
    """
    SQLite database for tracking processed emails.
    Prevents duplicate processing and maintains processing history.
    """

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize the email database.

        Args:
            db_path: Path to SQLite database file (defaults to data/automation.db)
        """
        self.db_path = db_path or (Config.PROJECT_ROOT / "data" / "automation.db")
        self.logger = logging.getLogger(__name__)

        # Ensure data directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize database schema
        self._initialize_schema()

    @contextmanager
    def _get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            self.logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()

    def _initialize_schema(self) -> None:
        """Create database tables if they don't exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Processed emails table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS processed_emails (
                    email_id TEXT PRIMARY KEY,
                    claim_number TEXT NOT NULL,
                    sender TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    received_timestamp TEXT NOT NULL,
                    processed_timestamp TEXT NOT NULL,
                    status TEXT NOT NULL,
                    error_message TEXT,
                    retry_count INTEGER DEFAULT 0
                )
            """
            )

            # Index for faster lookups
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_claim_number
                ON processed_emails(claim_number)
            """
            )

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_status
                ON processed_emails(status)
            """
            )

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_processed_timestamp
                ON processed_emails(processed_timestamp)
            """
            )

            self.logger.debug("Database schema initialized")

    def is_processed(self, email_id: str) -> bool:
        """
        Check if an email has already been processed.

        Args:
            email_id: Unique email identifier

        Returns:
            True if email was already processed, False otherwise
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT 1 FROM processed_emails WHERE email_id = ?", (email_id,)
            )
            result = cursor.fetchone()
            return result is not None

    def mark_processed(
        self,
        email_id: str,
        claim_number: str,
        sender: str,
        subject: str,
        received_timestamp: datetime,
        status: str = "success",
        error_message: Optional[str] = None,
    ) -> None:
        """
        Mark an email as processed in the database.

        Args:
            email_id: Unique email identifier
            claim_number: Extracted claim number
            sender: Email sender
            subject: Email subject
            received_timestamp: When email was received
            status: Processing status ('success', 'failed', 'pending')
            error_message: Error message if processing failed
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT OR REPLACE INTO processed_emails
                (email_id, claim_number, sender, subject, received_timestamp,
                 processed_timestamp, status, error_message, retry_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
            """,
                (
                    email_id,
                    claim_number,
                    sender,
                    subject,
                    received_timestamp.isoformat(),
                    datetime.now().isoformat(),
                    status,
                    error_message,
                ),
            )

            self.logger.info(f"Marked email {email_id} as {status}")

    def increment_retry_count(self, email_id: str) -> int:
        """
        Increment retry count for a failed email.

        Args:
            email_id: Unique email identifier

        Returns:
            New retry count
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                UPDATE processed_emails
                SET retry_count = retry_count + 1
                WHERE email_id = ?
            """,
                (email_id,),
            )

            cursor.execute(
                "SELECT retry_count FROM processed_emails WHERE email_id = ?",
                (email_id,),
            )

            result = cursor.fetchone()
            retry_count = result["retry_count"] if result else 0

            self.logger.info(f"Email {email_id} retry count: {retry_count}")
            return retry_count

    def get_retry_count(self, email_id: str) -> int:
        """
        Get current retry count for an email.

        Args:
            email_id: Unique email identifier

        Returns:
            Current retry count (0 if not found)
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT retry_count FROM processed_emails WHERE email_id = ?",
                (email_id,),
            )
            result = cursor.fetchone()
            return result["retry_count"] if result else 0

    def get_failed_emails(self, max_retries: int = 3) -> List[dict]:
        """
        Get emails that failed processing and haven't exceeded retry limit.

        Args:
            max_retries: Maximum number of retries allowed

        Returns:
            List of failed email records
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT * FROM processed_emails
                WHERE status = 'failed' AND retry_count < ?
                ORDER BY received_timestamp DESC
            """,
                (max_retries,),
            )

            return [dict(row) for row in cursor.fetchall()]

    def get_processing_stats(self, days: int = 7) -> dict:
        """
        Get processing statistics for the last N days.

        Args:
            days: Number of days to look back

        Returns:
            Dictionary with processing statistics
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Total processed
            cursor.execute(
                """
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
                FROM processed_emails
                WHERE processed_timestamp >= datetime('now', '-' || ? || ' days')
            """,
                (days,),
            )

            row = cursor.fetchone()

            return {
                "total": row["total"] or 0,
                "successful": row["successful"] or 0,
                "failed": row["failed"] or 0,
                "success_rate": (
                    (row["successful"] / row["total"] * 100)
                    if row["total"] > 0
                    else 0
                ),
            }

    def get_emails_by_claim(self, claim_number: str) -> List[dict]:
        """
        Get all processed emails for a specific claim number.

        Args:
            claim_number: Claim number to search for

        Returns:
            List of email records for this claim
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT * FROM processed_emails
                WHERE claim_number = ?
                ORDER BY received_timestamp DESC
            """,
                (claim_number,),
            )

            return [dict(row) for row in cursor.fetchall()]

    def cleanup_old_records(self, days: int = 90) -> int:
        """
        Delete successfully processed records older than N days.
        Keeps failed records for troubleshooting.

        Args:
            days: Number of days to retain records

        Returns:
            Number of records deleted
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                DELETE FROM processed_emails
                WHERE status = 'success'
                AND processed_timestamp < datetime('now', '-' || ? || ' days')
            """,
                (days,),
            )

            deleted_count = cursor.rowcount
            self.logger.info(f"Cleaned up {deleted_count} old records")

            return deleted_count


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    db = EmailDatabase()

    # Test operations
    print("Testing email database...")

    email_id = "test_123"
    if not db.is_processed(email_id):
        print(f"Email {email_id} not processed yet, adding...")
        db.mark_processed(
            email_id=email_id,
            claim_number="12345",
            sender="test@example.com",
            subject="Test claim #12345",
            received_timestamp=datetime.now(),
            status="success",
        )
    else:
        print(f"Email {email_id} already processed")

    # Get stats
    stats = db.get_processing_stats()
    print(f"\nProcessing stats (last 7 days): {stats}")

    # Get emails for a claim
    emails = db.get_emails_by_claim("12345")
    print(f"\nEmails for claim #12345: {len(emails)}")
