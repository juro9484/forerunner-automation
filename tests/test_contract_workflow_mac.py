#!/usr/bin/env python3
"""
Mac-specific test for the complete contract workflow end-to-end.
Uses Mac-compatible browser launch settings.

1. Parse contract PDF with Claude
2. Create claim in Claim Titan
3. Add policy information
4. Verify claim was created
"""

import sys
import logging
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from contract_parser import ContractParser
from playwright.sync_api import sync_playwright
from config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def create_claim_with_mac_browser(client_data):
    """
    Create claim using Playwright with Mac-specific browser settings.

    Args:
        client_data: ClientData object from contract parsing

    Returns:
        bool: True if successful
    """
    from claim_titan_bot import ClaimCreationResult
    from datetime import datetime

    playwright = None
    browser = None

    try:
        # Start Playwright
        logger.info("Starting Playwright with Mac-specific settings...")
        playwright = sync_playwright().start()

        # Launch Firefox browser (more stable on Mac than Chromium)
        logger.info("Launching Firefox browser...")
        browser = playwright.firefox.launch(
            headless=False  # Visible browser for recording
        )

        logger.info("Creating browser page...")
        # Create context with large viewport for fullscreen recording
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},  # Full HD for recording
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = context.new_page()

        page.set_default_timeout(30000)

        logger.info("✓ Browser opened successfully\n")

        # Login to Claim Titan
        logger.info("Logging into Claim Titan...")
        page.goto("https://claimtitan.com/welcome")
        page.wait_for_load_state('load')

        # Fill login form
        page.locator('input[name="email"]').fill(Config.CLAIM_TITAN_USER)
        page.locator('input[name="password"]').fill(Config.CLAIM_TITAN_PASS)
        page.locator('button[type="submit"]').click()

        # Wait for login
        page.wait_for_load_state('load')
        page.wait_for_timeout(2000)

        logger.info("✓ Logged in successfully\n")

        # Now use the claim_titan_bot logic for creating claim
        # Import here to avoid circular imports
        from claim_titan_bot import ClaimTitanBot

        # Create a bot instance but monkey-patch it to use our browser
        bot = ClaimTitanBot(headless=False)
        bot.playwright = playwright
        bot.browser = browser
        bot.page = page

        # Now create the claim
        logger.info("Creating claim...")
        result = bot.create_claim(client_data)

        if result.success:
            logger.info("\n" + "="*80)
            logger.info("✓ SUCCESS! Claim created in Claim Titan")
            logger.info("="*80)
            logger.info(f"Client: {result.client_name}")
            logger.info(f"Claim URL: {result.claim_url}")
            logger.info("="*80)

            # Keep browser open for user to verify
            logger.info("\nBrowser will stay open for 60 seconds for you to verify...")
            logger.info("Press Ctrl+C to close early\n")

            try:
                page.wait_for_timeout(60000)
            except KeyboardInterrupt:
                logger.info("\nClosing browser...")

            return True
        else:
            logger.error(f"\n✗ Claim creation failed: {result.error_message}")
            if result.screenshot_path:
                logger.error(f"Screenshot saved: {result.screenshot_path}")

            # Keep browser open to debug
            logger.info("\nBrowser will stay open for 30 seconds so you can see the error...")
            page.wait_for_timeout(30000)

            return False

    except Exception as e:
        logger.error(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Cleanup
        if browser:
            browser.close()
        if playwright:
            playwright.stop()


def main():
    # Get contract path from command line argument or use default
    if len(sys.argv) > 1:
        contract_path = sys.argv[1]
    else:
        # Default path
        contract_path = "/Users/juanrodriguez/Downloads/Hovda_Full_Contract.pdf"
        logger.warning(f"No contract path provided, using default: {contract_path}")
        logger.info("Usage: python test_contract_workflow_mac.py <path_to_contract.pdf>\n")

    # Check if file exists
    if not Path(contract_path).exists():
        logger.error(f"Contract file not found: {contract_path}")
        logger.error("Please provide a valid path to a contract PDF")
        sys.exit(1)

    logger.info("="*80)
    logger.info("CONTRACT WORKFLOW TEST (Mac Version)")
    logger.info("="*80)
    logger.info(f"Contract: {contract_path}\n")

    # Step 1: Parse contract
    logger.info("STEP 1: Parsing contract with Claude AI...")
    logger.info("-"*80)
    try:
        parser = ContractParser()
        client_data = parser.parse_contract(contract_path)

        logger.info("\n✓ Contract parsed successfully!")
        logger.info("\nExtracted Client Data:")
        logger.info(f"  Name: {client_data.first_name} {client_data.last_name or ''}")
        logger.info(f"  Email: {client_data.email or '(not found)'}")
        logger.info(f"  Phone: {client_data.phone or '(not found)'}")
        logger.info(f"  Address: {client_data.street_address}")
        logger.info(f"           {client_data.city}, {client_data.state} {client_data.zipcode}")
        logger.info(f"  Insurance: {client_data.insurance_company or '(not found)'}")
        logger.info(f"  Policy #: {client_data.policy_number or '(not found)'}")
        logger.info(f"  Claim #: {client_data.claim_number or '(not found)'}")
        logger.info(f"  Loss Type: {client_data.loss_type or '(not found)'}")
        logger.info(f"  Loss Date: {client_data.loss_date or '(not found)'}")

    except Exception as e:
        logger.error(f"\n✗ Contract parsing failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Step 2: Create claim in Claim Titan
    logger.info("\n" + "="*80)
    logger.info("STEP 2: Creating claim in Claim Titan...")
    logger.info("-"*80)

    success = create_claim_with_mac_browser(client_data)

    if success:
        logger.info("\n" + "="*80)
        logger.info("✓ TEST COMPLETED SUCCESSFULLY!")
        logger.info("="*80)
        logger.info("\nYou can now:")
        logger.info("  1. Review the created claim in Claim Titan")
        logger.info("  2. Use this recording for your website demo")
        logger.info("  3. Delete the test claim if needed")
        logger.info("="*80 + "\n")
        sys.exit(0)
    else:
        logger.error("\n" + "="*80)
        logger.error("✗ TEST FAILED")
        logger.error("="*80 + "\n")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n\nTest interrupted by user\n")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n✗ Test failed: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
