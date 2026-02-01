#!/usr/bin/env python3
"""
Test script to explore Claim Titan's client creation workflow.
Opens browser, logs in, navigates to Claims page, and waits for manual exploration.
"""

import sys
import time
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claim_titan_bot import ClaimTitanBot
from config import Config

def main():
    print("=" * 80)
    print("Claim Titan Client Creation Exploration")
    print("=" * 80)

    # Initialize bot with headless=False so we can see the browser
    bot = ClaimTitanBot(headless=False)

    try:
        print("\n1. Connecting to Claim Titan and logging in...")
        bot.connect()
        print("✓ Logged in successfully")

        print("\n2. Navigating to Claims page...")
        bot.page.goto("https://claimtitan.com/claims")
        bot.page.wait_for_load_state('networkidle')
        print("✓ On Claims page")

        # Take a screenshot of claims page
        screenshot_path = Path(__file__).parent.parent / "screenshots" / "claims_page.png"
        screenshot_path.parent.mkdir(exist_ok=True)
        bot.page.screenshot(path=str(screenshot_path))
        print(f"✓ Screenshot saved: {screenshot_path}")

        print("\n3. Clicking 'Add Claim' button to open modal...")
        # Click the "Add Claim" button
        add_claim_button = bot.page.locator('a.button.is-primary:has-text("Add")')
        add_claim_button.click()
        print("✓ Clicked Add Claim button")

        # Wait a moment for modal to appear
        time.sleep(2)

        # Take screenshot of modal
        modal_screenshot = Path(__file__).parent.parent / "screenshots" / "add_claim_modal.png"
        bot.page.screenshot(path=str(modal_screenshot))
        print(f"✓ Screenshot of modal saved: {modal_screenshot}")

        print("\n" + "=" * 80)
        print("Browser is now open on the Claims page.")
        print("INSTRUCTIONS:")
        print("1. Look for a 'New Client' or 'Create Client' button")
        print("2. Click it and explore the form")
        print("3. Note all the fields (required vs optional)")
        print("4. Take screenshots if needed")
        print("5. When done, press Ctrl+C here to close the browser")
        print("=" * 80)

        # Keep the browser open for manual exploration
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n\nClosing browser...")

    finally:
        bot.disconnect()
        print("✓ Browser closed")
        print("\nDone! Share what you found and we'll build the automation.")

if __name__ == "__main__":
    main()
