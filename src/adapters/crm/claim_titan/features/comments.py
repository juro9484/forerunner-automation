"""
Comments Feature for Claim Titan.
Handles posting notes to claims and uploading attachments.

NOTE: This currently delegates to methods in the adapter.
TODO: Extract note-posting and attachment upload logic here.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from ..exceptions import PostError


@dataclass
class ClaimTitanResult:
    """Result of posting a note to Claim Titan."""
    claim_number: str
    note_title: str
    note_description: str
    success: bool
    timestamp: datetime
    error_message: Optional[str] = None
    screenshot_path: Optional[str] = None


class CommentsFeature:
    """
    Comments feature for Claim Titan.
    Posts notes and optionally uploads attachments to claims.
    """

    def __init__(self, adapter, upload_attachments: bool = False):
        """
        Initialize comments feature.

        Args:
            adapter: ClaimTitanAdapter instance
            upload_attachments: Whether to upload attachments
        """
        self.adapter = adapter
        self.upload_attachments = upload_attachments
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"CommentsFeature initialized (upload_attachments={upload_attachments})")

    def process(self, email_data, summary, timeout_minutes: int = 5) -> ClaimTitanResult:
        """
        Process email: post note and optionally upload attachments.

        Args:
            email_data: EmailData object
            summary: AI-generated summary (has .title and .description)
            timeout_minutes: Timeout for operation

        Returns:
            ClaimTitanResult
        """
        self.logger.info(f"Processing comments for claim {email_data.claim_number}")

        # For now, delegate to existing claim_titan_bot logic
        # TODO: Move note-posting logic here
        try:
            # Import the old bot temporarily
            import sys
            import os
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
            from claim_titan_bot import ClaimTitanBot, ClaimTitanResult as OldResult

            # Use existing bot with same browser session
            # This is a temporary bridge until we fully refactor
            bot = ClaimTitanBot.__new__(ClaimTitanBot)
            bot.page = self.adapter.page
            bot.logger = self.logger
            bot.attachment_handler = self.adapter.attachment_handler

            # Call existing post_note method
            result = bot.post_note(
                claim_number=email_data.claim_number,
                title=summary.title,
                description=summary.description,
                timeout_minutes=timeout_minutes
            )

            # Convert old result to new result
            return ClaimTitanResult(
                claim_number=result.claim_number,
                note_title=result.note_title,
                note_description=result.note_description,
                success=result.success,
                timestamp=result.timestamp,
                error_message=result.error_message,
                screenshot_path=result.screenshot_path
            )

        except Exception as e:
            self.logger.error(f"Failed to process comments: {e}")
            return ClaimTitanResult(
                claim_number=email_data.claim_number,
                note_title=summary.title,
                note_description=summary.description,
                success=False,
                timestamp=datetime.now(),
                error_message=str(e),
                screenshot_path=None
            )
