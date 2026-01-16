"""
Test script for the Claim Titan bot.
Tests browser automation, login, claim search, and note posting.
"""

import sys
import logging
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claim_titan_bot import ClaimTitanBot, ClaimTitanError


def setup_logging():
    """Configure logging for tests."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def test_login():
    """Test 1: Login to Claim Titan."""
    print("\n" + "="*70)
    print("TEST 1: Login")
    print("="*70 + "\n")

    try:
        bot = ClaimTitanBot(headless=False)
        bot.connect()
        print("✅ Login successful!")
        bot.disconnect()
        return True
    except Exception as e:
        print(f"❌ Login failed: {e}")
        return False


def test_post_note():
    """Test 2: Post a note to a claim."""
    print("\n" + "="*70)
    print("TEST 2: Post Note to Claim")
    print("="*70 + "\n")

    # CHANGE THESE FOR YOUR TEST
    test_claim = "75-79G4-03P"  # Change to a real claim in your system
    test_title = "1.15.26 Test Note from Automation"
    test_description = "This is a test note posted by the Claim Titan bot. If you see this, the automation is working correctly!"

    try:
        with ClaimTitanBot(headless=False) as bot:
            print(f"Posting to claim: {test_claim}\n")

            result = bot.post_note(
                claim_number=test_claim,
                title=test_title,
                description=test_description
            )

            print("\n" + "-"*70)
            print("RESULT:")
            print("-"*70)
            print(f"Success: {result.success}")
            print(f"Claim: {result.claim_number}")
            print(f"Title: {result.note_title}")
            print(f"Timestamp: {result.timestamp}")

            if not result.success:
                print(f"\nError: {result.error_message}")
                if result.screenshot_path:
                    print(f"Screenshot: {result.screenshot_path}")

            print("-"*70)

            if result.success:
                print("\n✅ Note posted successfully!")
                print("Check Claim Titan to verify the note was added.")
                return True
            else:
                print("\n❌ Note posting failed!")
                return False

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        logging.exception("Test exception:")
        return False


def test_hyphen_retry():
    """Test 3: Search with and without hyphens."""
    print("\n" + "="*70)
    print("TEST 3: Hyphen Retry Logic")
    print("="*70 + "\n")

    # Test with a claim that might need hyphen removal
    test_claim_with_hyphens = "01-100-912929"  # Change to match your data

    try:
        with ClaimTitanBot(headless=False) as bot:
            print(f"Searching for claim: {test_claim_with_hyphens}")
            print("Bot will try with hyphens, then without if needed\n")

            # Just test the search, don't post a note
            found_format = bot._search_claim(test_claim_with_hyphens)

            print(f"\n✅ Claim found with format: {found_format}")
            return True

    except ClaimTitanError as e:
        print(f"\n❌ Search failed: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        logging.exception("Test exception:")
        return False


def test_verification():
    """Test 4: Claim number verification."""
    print("\n" + "="*70)
    print("TEST 4: Claim Verification")
    print("="*70 + "\n")

    test_claim = "75-79G4-03P"  # Change to a real claim

    try:
        with ClaimTitanBot(headless=False) as bot:
            print(f"Testing verification for claim: {test_claim}\n")

            # Search and open claim
            found_format = bot._search_claim(test_claim)
            bot._open_claim(found_format, test_claim)

            print("\n✅ Claim verification passed!")
            print("Bot verified we're on the correct claim page.")
            return True

    except ClaimTitanError as e:
        print(f"\n❌ Verification failed: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        logging.exception("Test exception:")
        return False


def main():
    """Run all tests."""
    setup_logging()

    print("\n" + "="*70)
    print("CLAIM TITAN BOT TEST SUITE")
    print("="*70)
    print("\nIMPORTANT: Update test_claim variables in the code")
    print("to match real claims in your Claim Titan system.")
    print("="*70)

    # Ask user which tests to run
    print("\nAvailable tests:")
    print("1. Login only")
    print("2. Post note (full end-to-end test)")
    print("3. Hyphen retry logic")
    print("4. Claim verification")
    print("5. Run all tests")

    choice = input("\nEnter test number (1-5): ").strip()

    results = []

    if choice == "1":
        results.append(("Login Test", test_login()))
    elif choice == "2":
        results.append(("Post Note Test", test_post_note()))
    elif choice == "3":
        results.append(("Hyphen Retry Test", test_hyphen_retry()))
    elif choice == "4":
        results.append(("Verification Test", test_verification()))
    elif choice == "5":
        results.append(("Login Test", test_login()))
        results.append(("Post Note Test", test_post_note()))
        results.append(("Hyphen Retry Test", test_hyphen_retry()))
        results.append(("Verification Test", test_verification()))
    else:
        print("Invalid choice. Running Test 2 (Post Note)...")
        results.append(("Post Note Test", test_post_note()))

    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")

    total_passed = sum(1 for _, passed in results if passed)
    total_tests = len(results)

    print(f"\nTotal: {total_passed}/{total_tests} tests passed")
    print("="*70 + "\n")

    if total_passed == total_tests:
        print("🎉 All tests passed! The bot is ready for production.\n")
    else:
        print("⚠️  Some tests failed. Check errors above.\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.\n")
    except Exception as e:
        print(f"\n✗ Test suite failed: {e}\n")
        logging.exception("Fatal error:")
