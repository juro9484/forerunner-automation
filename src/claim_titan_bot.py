"""
Claim Titan Bot module for Forerunner Claims Automation.
Automates posting notes to the Claim Titan CRM using Playwright browser automation.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from playwright.sync_api import sync_playwright, Browser, Page, Playwright

from config import Config


@dataclass
class ClaimTitanResult:
    """
    Result of posting a note to Claim Titan.

    Attributes:
        claim_number: The claim number the note was posted to
        note_title: The title of the note
        note_description: The description/body of the note
        success: Whether the note was successfully posted
        timestamp: When the operation was attempted
        error_message: Error message if failed
        screenshot_path: Path to error screenshot if captured
    """
    claim_number: str
    note_title: str
    note_description: str
    success: bool
    timestamp: datetime
    error_message: Optional[str] = None
    screenshot_path: Optional[str] = None


class ClaimTitanError(Exception):
    """Base exception for Claim Titan bot errors."""
    pass


class LoginError(ClaimTitanError):
    """Raised when login to Claim Titan fails."""
    pass


class SearchError(ClaimTitanError):
    """Raised when claim search fails."""
    pass


class PostError(ClaimTitanError):
    """Raised when note posting fails."""
    pass


class BrowserError(ClaimTitanError):
    """Raised when browser automation fails."""
    pass


class ClaimTitanBot:
    """
    Automates posting notes to Claim Titan CRM.

    This class uses Playwright to automate browser interactions with
    Claim Titan, including login, claim search, and note posting.
    """

    def __init__(self,
                 username: Optional[str] = None,
                 password: Optional[str] = None,
                 base_url: Optional[str] = None,
                 headless: Optional[bool] = None):
        """
        Initialize the Claim Titan bot.

        Args:
            username: Claim Titan username (defaults to Config.CLAIM_TITAN_USER)
            password: Claim Titan password (defaults to Config.CLAIM_TITAN_PASS)
            base_url: Claim Titan URL (defaults to Config.CLAIM_TITAN_URL)
            headless: Run browser in headless mode (defaults to Config.BROWSER_HEADLESS)
        """
        self.username = username or Config.CLAIM_TITAN_USER
        self.password = password or Config.CLAIM_TITAN_PASS
        self.base_url = base_url or Config.CLAIM_TITAN_URL
        self.headless = headless if headless is not None else Config.BROWSER_HEADLESS

        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.logger = logging.getLogger(__name__)

        if not self.username or not self.password:
            raise ValueError("Claim Titan credentials not configured in .env file")

        self.logger.info("ClaimTitanBot initialized")

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensure cleanup."""
        self.disconnect()
        return False

    def connect(self):
        """Start Playwright browser and login to Claim Titan."""
        self.logger.info("Starting browser and logging in to Claim Titan...")

        try:
            # Start Playwright
            self.playwright = sync_playwright().start()

            # Launch browser with cross-platform args
            self.browser = self.playwright.chromium.launch(
                headless=self.headless,
                args=[
                    '--disable-blink-features=AutomationControlled',  # Hide automation
                    '--disable-dev-shm-usage',  # Overcome limited resource problems
                    '--no-sandbox',  # Required for running as service/root
                    '--disable-setuid-sandbox',  # Required for Linux/macOS
                    '--disable-gpu',  # Helps with Windows service stability
                    '--disable-software-rasterizer'  # Windows headless stability
                ]
            )
            self.page = self.browser.new_page()

            # Set user agent to look like a real browser
            self.page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            })

            # Set default timeout
            self.page.set_default_timeout(30000)  # 30 seconds

            # Login
            self._login()

            self.logger.info("✓ Connected and logged in successfully")

        except Exception as e:
            self.logger.error(f"Failed to connect: {e}")
            self.disconnect()
            raise BrowserError(f"Failed to initialize browser: {e}")

    def disconnect(self):
        """Close browser and cleanup resources."""
        self.logger.info("Closing browser...")

        try:
            if self.page:
                self.page.close()
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()

            self.logger.info("✓ Browser closed")

        except Exception as e:
            self.logger.warning(f"Error during cleanup: {e}")

    def _login(self):
        """Login to Claim Titan."""
        self.logger.info(f"Navigating to {self.base_url}")

        try:
            # Navigate to login page
            self.logger.info("Loading page...")
            self.page.goto(self.base_url, wait_until='domcontentloaded')
            self.logger.info("Page loaded")

            # Fill credentials
            self.logger.info("Filling login credentials...")
            self.page.locator('#email').fill(self.username)
            self.page.locator('#password').fill(self.password)

            # Submit form
            self.logger.info("Submitting login form...")
            self.page.locator('button[type="submit"]').click()

            # Wait for navigation
            self.page.wait_for_load_state('networkidle')

            # Verify login success by checking for search box
            if not self.page.locator('input[name="search"]').is_visible():
                raise LoginError("Login failed - search box not found on dashboard")

            self.logger.info("✓ Login successful")

        except LoginError:
            raise
        except Exception as e:
            raise LoginError(f"Login failed: {e}")

    def post_note(self, claim_number: str, title: str, description: str) -> ClaimTitanResult:
        """
        Post a note to a claim in Claim Titan.

        Args:
            claim_number: Claim number to search for (may have hyphens)
            title: Note title
            description: Note description

        Returns:
            ClaimTitanResult with success status and details
        """
        self.logger.info(f"Posting note to claim {claim_number}")

        try:
            # Search for claim (tries with/without hyphens)
            found_claim_format = self._search_claim(claim_number)

            # Open claim page and verify we're on the right claim
            self._open_claim(found_claim_format, claim_number)

            # Open notes sidebar and form
            self._open_notes_form()

            # Fill and submit note
            self._fill_note_form(title, description)

            self.logger.info(f"✓ Successfully posted note to claim {claim_number}")

            return ClaimTitanResult(
                claim_number=claim_number,
                note_title=title,
                note_description=description,
                success=True,
                timestamp=datetime.now()
            )

        except Exception as e:
            self.logger.error(f"Failed to post note for {claim_number}: {e}")
            screenshot_path = self._take_screenshot(claim_number)

            return ClaimTitanResult(
                claim_number=claim_number,
                note_title=title,
                note_description=description,
                success=False,
                timestamp=datetime.now(),
                error_message=str(e),
                screenshot_path=screenshot_path
            )

    def _search_claim(self, claim_number: str) -> str:
        """
        Search for a claim by number, trying with and without hyphens.

        Args:
            claim_number: Claim number to search for

        Returns:
            The claim number format that found results

        Raises:
            SearchError: If claim not found
        """
        self.logger.info(f"Searching for claim: {claim_number}")

        search_box = self.page.locator('input[name="search"]')

        # Try with original format first
        search_box.clear()
        search_box.fill(claim_number)
        search_box.press('Enter')
        self.page.wait_for_load_state('networkidle')

        # Check if results found
        if self._has_claim_results():
            self.logger.info(f"✓ Found claim with format: {claim_number}")
            return claim_number

        # If no results and claim has hyphens, try without hyphens
        if '-' in claim_number:
            claim_no_hyphens = claim_number.replace('-', '')
            self.logger.info(f"No results with hyphens, trying without: {claim_no_hyphens}")

            search_box.clear()
            search_box.fill(claim_no_hyphens)
            search_box.press('Enter')
            self.page.wait_for_load_state('networkidle')

            if self._has_claim_results():
                self.logger.info(f"✓ Found claim with format: {claim_no_hyphens}")
                return claim_no_hyphens

        raise SearchError(f"Claim {claim_number} not found (tried with and without hyphens)")

    def _has_claim_results(self) -> bool:
        """
        Check if search returned any claim results.

        Returns:
            True if results found, False otherwise
        """
        try:
            # Look for the claims section header
            results_header = self.page.locator('h4:has-text("Claim")')
            return results_header.is_visible()
        except Exception:
            return False

    def _open_claim(self, claim_number: str, original_claim: str):
        """
        Click on claim in search results and verify we're on the right claim.

        Args:
            claim_number: The claim number format that found results
            original_claim: The original claim number from the email

        Raises:
            SearchError: If claim link not found
            PostError: If claim verification fails
        """
        self.logger.info(f"Opening claim: {claim_number}")

        # Find container with claim number, then click the /claims/ link
        claim_link = self.page.locator(
            f'div.columns:has-text("{claim_number}") a[href*="/claims/"]'
        ).first

        if not claim_link.is_visible():
            raise SearchError(f"Claim {claim_number} not found in search results")

        claim_link.click()
        self.page.wait_for_load_state('networkidle')

        # CRITICAL: Verify we're on the correct claim before posting
        self._verify_claim_number(original_claim)

        self.logger.info(f"✓ Opened claim page")

    def _verify_claim_number(self, expected_claim: str):
        """
        Verify we're on the correct claim page by checking the claim number.

        Args:
            expected_claim: The claim number we expect to see

        Raises:
            PostError: If claim number doesn't match
        """
        self.logger.info(f"Verifying claim number: {expected_claim}")

        try:
            # Find the claim number on the page
            # Find the "Claim Number" label, then get its parent container, then find the value element
            claim_label = self.page.locator('p.text-grey-light.text-xs:has-text("Claim Number")')

            # Get the parent flex container
            flex_container = claim_label.locator('xpath=..')

            # Within that specific container, get the second <p> element (the value, not the label)
            claim_number_element = flex_container.locator('p.text-grey.font-500').first

            if not claim_number_element.is_visible():
                raise PostError("Cannot verify claim number - element not found on page")

            page_claim_number = claim_number_element.inner_text().strip()

            # Normalize both claim numbers (remove hyphens and compare)
            normalized_expected = expected_claim.replace('-', '').upper()
            normalized_page = page_claim_number.replace('-', '').upper()

            if normalized_expected != normalized_page:
                raise PostError(
                    f"Claim number mismatch! Expected: {expected_claim}, "
                    f"Found on page: {page_claim_number}"
                )

            self.logger.info(f"✓ Verified claim number: {page_claim_number}")

        except PostError:
            raise
        except Exception as e:
            raise PostError(f"Failed to verify claim number: {e}")

    def _open_notes_form(self):
        """Open notes sidebar and add note form."""
        self.logger.info("Opening notes form...")

        try:
            # Step 1: Click Notes sidebar button to open notes panel
            notes_sidebar_button = self.page.locator('button.sidebar-nav-item:has-text("Notes")')
            notes_sidebar_button.click()
            self.logger.info("Clicked Notes sidebar button")

            # Wait a moment for sidebar to open
            self.page.wait_for_timeout(500)

            # Step 2: Click "New Note" button inside the notes panel
            new_note_button = self.page.locator('a.button:has-text("New Note")')
            new_note_button.click()
            self.logger.info("Clicked New Note button")

            # Wait for form to appear
            self.page.wait_for_selector('input[name="title"]', state='visible')

            self.logger.info("✓ Notes form opened")

        except Exception as e:
            raise PostError(f"Failed to open notes form: {e}")

    def _fill_note_form(self, title: str, description: str):
        """
        Fill out and submit note form.

        Args:
            title: Note title
            description: Note description

        Raises:
            PostError: If form filling or submission fails
        """
        self.logger.info("Filling note form...")

        try:
            # Fill fields
            self.page.locator('input[name="title"]').fill(title)
            self.page.locator('textarea[name="description"]').fill(description)

            self.logger.info("Submitting note...")

            # Submit
            self.page.locator('button[type="submit"].is-primary').click()

            # Wait for submission to complete
            self.page.wait_for_load_state('networkidle')

            self.logger.info("✓ Note submitted")

        except Exception as e:
            raise PostError(f"Failed to fill/submit note form: {e}")

    def _take_screenshot(self, claim_number: str) -> str:
        """
        Take screenshot on error for debugging.

        Args:
            claim_number: Claim number for filename

        Returns:
            Path to screenshot file
        """
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            # Sanitize claim number for filename
            safe_claim = claim_number.replace('/', '_').replace('\\', '_')
            filename = f"error_{safe_claim}_{timestamp}.png"
            filepath = Config.SCREENSHOTS_DIR / filename

            self.page.screenshot(path=str(filepath))
            self.logger.error(f"Screenshot saved: {filepath}")

            return str(filepath)

        except Exception as e:
            self.logger.error(f"Failed to take screenshot: {e}")
            return ""


def main():
    """
    Example usage of the ClaimTitanBot.
    This is for testing purposes only.
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Test with a sample note
    test_claim = "75-79G4-03P"
    test_title = "1.15.26 Test Note from Bot"
    test_description = "This is a test note posted by the Claim Titan bot automation system."

    try:
        # Initialize bot
        print("\n" + "="*70)
        print("CLAIM TITAN BOT TEST")
        print("="*70 + "\n")

        with ClaimTitanBot(headless=False) as bot:
            print(f"Testing with claim: {test_claim}\n")

            # Post note
            result = bot.post_note(
                claim_number=test_claim,
                title=test_title,
                description=test_description
            )

            # Display result
            print("\n" + "="*70)
            print("RESULT")
            print("="*70)
            print(f"Success: {result.success}")
            print(f"Claim: {result.claim_number}")
            print(f"Title: {result.note_title}")
            print(f"Timestamp: {result.timestamp}")

            if not result.success:
                print(f"Error: {result.error_message}")
                if result.screenshot_path:
                    print(f"Screenshot: {result.screenshot_path}")

            print("="*70 + "\n")

    except Exception as e:
        print(f"\n✗ Test failed: {e}\n")
        logging.exception("Test failed with exception:")


if __name__ == "__main__":
    main()
