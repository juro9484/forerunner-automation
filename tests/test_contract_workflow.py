#!/usr/bin/env python3
"""
Test the complete contract workflow end-to-end:
1. Parse contract PDF with Claude
2. Create claim in Claim Titan
3. Verify claim was created
"""

import sys
import logging
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from contract_parser import ContractParser
from claim_titan_bot import ClaimTitanBot

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    # Get contract path from command line argument or use default
    if len(sys.argv) > 1:
        contract_path = sys.argv[1]
    else:
        # Default path (update this to your Windows path)
        contract_path = "/Users/juanrodriguez/Downloads/Hovda_Full Contract.pdf"
        logger.warning(f"No contract path provided, using default: {contract_path}")
        logger.info("Usage: python test_contract_workflow.py <path_to_contract.pdf>\n")

    # Check if file exists
    if not Path(contract_path).exists():
        logger.error(f"Contract file not found: {contract_path}")
        logger.error("Please provide a valid path to a contract PDF")
        sys.exit(1)

    logger.info("="*80)
    logger.info("CONTRACT WORKFLOW TEST")
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
        sys.exit(1)

    # Step 2: Create claim in Claim Titan
    logger.info("\n" + "="*80)
    logger.info("STEP 2: Creating claim in Claim Titan...")
    logger.info("-"*80)

    bot = None
    try:
        # Initialize bot (headless=False so you can watch)
        logger.info("Opening browser (headless=False for visibility)...")
        bot = ClaimTitanBot(headless=False)
        bot.connect()
        logger.info("✓ Browser opened and logged in\n")

        # Create claim
        logger.info("Creating claim...")
        result = bot.create_claim(client_data)

        if result.success:
            logger.info("\n" + "="*80)
            logger.info("✓ SUCCESS! Claim created in Claim Titan")
            logger.info("="*80)
            logger.info(f"Client: {result.client_name}")
            logger.info(f"Claim URL: {result.claim_url}")
            logger.info("="*80)
            logger.info("\nPlease verify in the browser that:")
            logger.info("  1. Policyholder name is correct")
            logger.info("  2. Address is filled")
            logger.info("  3. Insurance company is set (State Farm)")
            logger.info("  4. Loss type is set (fire)")
            logger.info("\nBrowser will stay open for 60 seconds for verification...")

            import time
            time.sleep(60)

        else:
            logger.error("\n" + "="*80)
            logger.error("✗ FAILED to create claim")
            logger.error("="*80)
            logger.error(f"Error: {result.error_message}")
            if result.screenshot_path:
                logger.error(f"Screenshot: {result.screenshot_path}")
            logger.error("="*80)
            logger.info("\nBrowser will stay open for 60 seconds for debugging...")

            import time
            time.sleep(60)
            sys.exit(1)

    except Exception as e:
        logger.error(f"\n✗ Unexpected error: {e}", exc_info=True)
        logger.info("\nBrowser will stay open for 60 seconds for debugging...")

        import time
        time.sleep(60)
        sys.exit(1)

    finally:
        if bot:
            logger.info("\nClosing browser...")
            bot.disconnect()
            logger.info("✓ Browser closed")


if __name__ == "__main__":
    main()
