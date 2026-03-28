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
        claim_number = email_data.claim_number
        self.logger.info(f"Processing comments for claim {claim_number}")

        # Set page timeout for this operation
        self.adapter.page.set_default_timeout(timeout_minutes * 60 * 1000)

        try:
            # Navigate to claims list if on a different claim page
            current_url = self.adapter.page.url
            if '/claims/' in current_url and current_url != 'https://claimtitan.com/claims':
                self.logger.info(f"  Currently on specific claim page, navigating to claims list...")
                self.adapter.page.goto('https://claimtitan.com/claims')
                self.adapter.page.wait_for_load_state('load', timeout=30000)
                self.adapter.page.wait_for_timeout(2000)

            # Use adapter's robust search_claim (same as check_deposit)
            found_variation = self.adapter.search_claim(claim_number)
            self.logger.info(f"  Found claim with variation: {found_variation}")

            # Open the claim
            if '/claims/' not in self.adapter.page.url or self.adapter.page.url == 'https://claimtitan.com/claims':
                self.adapter.open_claim(found_variation, claim_number)
                self.logger.info(f"  Opened claim page")

            # Open notes sidebar and form
            self._open_notes_form()

            # Fill and submit note
            self._fill_note_form(summary.title, summary.description)

            self.logger.info(f"✓ Successfully posted note to claim {claim_number}")

            return ClaimTitanResult(
                claim_number=claim_number,
                note_title=summary.title,
                note_description=summary.description,
                success=True,
                timestamp=datetime.now()
            )

        except Exception as e:
            self.logger.error(f"Failed to process comments: {e}")
            screenshot_path = self.adapter.take_screenshot(claim_number) if hasattr(self.adapter, 'take_screenshot') else None
            return ClaimTitanResult(
                claim_number=claim_number,
                note_title=summary.title,
                note_description=summary.description,
                success=False,
                timestamp=datetime.now(),
                error_message=str(e),
                screenshot_path=screenshot_path
            )

    def _open_notes_form(self):
        """Open notes sidebar and add note form with robust timeout handling."""
        self.logger.info("Opening notes form...")
        page = self.adapter.page

        max_retries = 3
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    self.logger.info(f"Retry attempt {attempt + 1}/{max_retries}...")

                # Wait for page to be fully loaded
                page.wait_for_load_state('load', timeout=60000)
                page.wait_for_timeout(3000)

                # Click Notes sidebar button
                self.logger.info("Looking for Notes sidebar button...")
                notes_sidebar_button = page.locator('button.sidebar-nav-item:has-text("Notes")')
                notes_sidebar_button.wait_for(state='visible', timeout=60000)
                self.logger.info("✓ Notes button found")

                notes_sidebar_button.scroll_into_view_if_needed(timeout=10000)
                page.wait_for_timeout(500)

                # Try click strategies
                click_success = False
                for strategy_name, click_fn in [
                    ("normal click", lambda: notes_sidebar_button.click(timeout=10000)),
                    ("force click", lambda: notes_sidebar_button.click(force=True, timeout=10000)),
                    ("JS click", lambda: page.evaluate("document.querySelector('button.sidebar-nav-item:has-text(\"Notes\")').click()")),
                ]:
                    try:
                        self.logger.info(f"Attempting {strategy_name} on Notes button...")
                        click_fn()
                        click_success = True
                        self.logger.info(f"✓ {strategy_name} succeeded")
                        break
                    except Exception as e:
                        self.logger.warning(f"{strategy_name} failed: {e}")

                if not click_success:
                    raise PostError("All click strategies failed for Notes button")

                page.wait_for_timeout(4000)

                # Verify notes panel opened
                new_note_button = page.locator('a.button:has-text("New Note")')
                new_note_button.wait_for(state='visible', timeout=10000)
                self.logger.info("✓ Notes panel confirmed open")

                # Click New Note
                new_note_button.scroll_into_view_if_needed(timeout=10000)
                page.wait_for_timeout(500)

                try:
                    new_note_button.click(timeout=10000)
                    self.logger.info("✓ Clicked New Note button")
                except Exception:
                    new_note_button.click(force=True, timeout=10000)
                    self.logger.info("✓ Force clicked New Note button")

                # Wait for note form
                page.wait_for_selector(
                    'form[action*="/notes"] input[name="title"]',
                    state='visible',
                    timeout=60000
                )
                self.logger.info("✓ Notes form opened successfully")
                return

            except Exception as e:
                self.logger.error(f"Attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    page.wait_for_timeout(3000)
                else:
                    raise PostError(f"Failed to open notes form after {max_retries} attempts: {e}")

    def _fill_note_form(self, title: str, description: str):
        """Fill out and submit note form."""
        self.logger.info("Filling note form...")
        page = self.adapter.page

        try:
            notes_form = page.locator('form[action*="/notes"]')
            notes_form.locator('input[name="title"]').fill(title)
            notes_form.locator('textarea[name="description"]').fill(description)

            self.logger.info("Submitting note...")
            save_button = notes_form.locator('button:has-text("Save Note")')
            save_button.wait_for(state='visible', timeout=5000)
            save_button.click()

            self.logger.info("Clicked Save Note button")
            page.wait_for_timeout(2000)
            self.logger.info("✓ Note submitted")

        except Exception as e:
            raise PostError(f"Failed to fill/submit note form: {e}")
