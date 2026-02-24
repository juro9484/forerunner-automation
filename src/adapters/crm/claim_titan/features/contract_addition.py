"""
Contract Addition Feature for Claim Titan.
Handles creating new claims from parsed contract data.

NOTE: This currently delegates to methods in claim_titan_bot.
TODO: Extract claim creation logic here.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from ..exceptions import ClaimTitanError


@dataclass
class ClaimCreationResult:
    """Result of creating a new claim."""
    client_name: str
    claim_url: Optional[str]
    success: bool
    timestamp: datetime
    error_message: Optional[str] = None
    screenshot_path: Optional[str] = None


class ContractAdditionFeature:
    """
    Contract addition feature for Claim Titan.
    Creates new claims from contract PDF data.
    """

    def __init__(self, adapter):
        """
        Initialize contract addition feature.

        Args:
            adapter: ClaimTitanAdapter instance
        """
        self.adapter = adapter
        self.logger = logging.getLogger(__name__)
        self.logger.info("ContractAdditionFeature initialized")

    def process(self, client_data, timeout_minutes: int = 10) -> ClaimCreationResult:
        """
        Process contract: create new claim in Claim Titan.

        Args:
            client_data: ClientData object from contract parser
            timeout_minutes: Timeout for operation

        Returns:
            ClaimCreationResult
        """
        client_name = f"{client_data.first_name} {client_data.last_name or ''}".strip()
        self.logger.info(f"Processing contract for client: {client_name}")

        # For now, delegate to existing claim_titan_bot logic
        # TODO: Move claim creation logic here
        try:
            # Import the old bot temporarily
            import sys
            import os
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
            from claim_titan_bot import ClaimTitanBot, ClaimCreationResult as OldResult

            # Use existing bot with same browser session
            bot = ClaimTitanBot.__new__(ClaimTitanBot)
            bot.page = self.adapter.page
            bot.logger = self.logger
            bot.attachment_handler = self.adapter.attachment_handler
            bot._robust_click = self.adapter.robust_click
            bot._take_screenshot = self.adapter.take_screenshot

            # Call existing create_claim method
            result = bot.create_claim(client_data, timeout_minutes=timeout_minutes)

            # Convert old result to new result
            return ClaimCreationResult(
                client_name=result.client_name,
                claim_url=result.claim_url,
                success=result.success,
                timestamp=result.timestamp,
                error_message=result.error_message,
                screenshot_path=result.screenshot_path
            )

        except Exception as e:
            self.logger.error(f"Failed to create claim: {e}")
            return ClaimCreationResult(
                client_name=client_name,
                claim_url=None,
                success=False,
                timestamp=datetime.now(),
                error_message=str(e),
                screenshot_path=None
            )
