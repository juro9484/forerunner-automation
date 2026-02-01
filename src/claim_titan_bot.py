"""
Claim Titan Bot module for Forerunner Claims Automation.
Automates posting notes to the Claim Titan CRM using Playwright browser automation.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict
from playwright.sync_api import sync_playwright, Browser, Page, Playwright

from config import Config
from attachment_handler import AttachmentHandler, AttachmentData

# Import ClientData for type hints
try:
    from contract_parser import ClientData
except ImportError:
    # Allow module to work even if contract_parser isn't available
    ClientData = None


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


@dataclass
class ClaimCreationResult:
    """
    Result of creating a new claim in Claim Titan.

    Attributes:
        client_name: The client's full name
        claim_url: URL of the created claim (if successful)
        success: Whether the claim was successfully created
        timestamp: When the operation was attempted
        error_message: Error message if failed
        screenshot_path: Path to error screenshot if captured
    """
    client_name: str
    claim_url: Optional[str]
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

        # Attachment handler for file operations
        self.attachment_handler = AttachmentHandler()

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
            self.logger.info("DEBUG: Starting Playwright...")
            self.playwright = sync_playwright().start()
            self.logger.info("DEBUG: Playwright started successfully")

            # Launch browser with cross-platform args
            self.logger.info(f"DEBUG: Launching browser (headless={self.headless})...")
            # Use minimal args for Mac stability
            launch_args = []
            if self.headless:
                # Only use these args in headless mode (Windows service)
                launch_args = [
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-gpu',
                ]

            self.browser = self.playwright.chromium.launch(
                headless=self.headless,
                args=launch_args
            )
            self.logger.info("DEBUG: Browser launched successfully")

            self.logger.info("DEBUG: Creating new page...")
            self.page = self.browser.new_page()
            self.logger.info("DEBUG: Page created successfully")

            # Set user agent to look like a real browser
            self.logger.info("DEBUG: Setting user agent...")
            self.page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            })

            # Set default timeout
            self.page.set_default_timeout(30000)  # 30 seconds
            self.logger.info("DEBUG: Browser configured, starting login...")

            # Login
            self._login()

            self.logger.info("✓ Connected and logged in successfully")

        except Exception as e:
            import traceback
            error_msg = str(e)
            error_type = type(e).__name__
            error_traceback = traceback.format_exc()

            self.logger.error("="*80)
            self.logger.error("BROWSER LAUNCH FAILED!")
            self.logger.error(f"Error message: {error_msg}")
            self.logger.error(f"Error type: {error_type}")
            self.logger.error(f"Full traceback:\n{error_traceback}")
            self.logger.error("="*80)

            self.disconnect()
            raise BrowserError(f"Failed to initialize browser: {error_msg}")

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

    def create_claim(self, client_data) -> ClaimCreationResult:
        """
        Create a new claim in Claim Titan from contract data.

        Args:
            client_data: ClientData object with client and property information

        Returns:
            ClaimCreationResult with success status and claim URL

        Raises:
            ClaimTitanError: If claim creation fails
        """
        client_name = f"{client_data.first_name} {client_data.last_name or ''}".strip()
        self.logger.info(f"Creating new claim for client: {client_name}")

        current_step = "initialization"
        try:
            # Navigate to Claims page
            current_step = "navigating to Claims page"
            self.logger.info(f"[STEP 1] Navigating to Claims page...")
            self.page.goto("https://claimtitan.com/claims")
            self.page.wait_for_load_state('networkidle', timeout=30000)
            self.logger.info("✓ [STEP 1 COMPLETE] On Claims page")

            # Click "Add Claim" button to open modal
            current_step = "clicking Add Claim button"
            self.logger.info(f"[STEP 2] Clicking Add Claim button...")
            try:
                add_claim_button = self.page.locator('a.button.is-primary:has-text("Add")')
                self._robust_click(add_claim_button, "Add Claim button")
                self.page.wait_for_timeout(2000)  # Wait for modal to appear
                self.logger.info("✓ [STEP 2 COMPLETE] Add Claim modal opened")
            except Exception as e:
                raise ClaimTitanError(f"Failed at STEP 2 (clicking Add Claim button): {e}")

            # Wait for policyholder form fields to be visible (they're shown by default)
            current_step = "waiting for policyholder form fields to appear"
            self.logger.info(f"[STEP 3] Waiting for policyholder form fields...")
            try:
                first_name_field = self.page.locator('input[name="first_name"]')
                first_name_field.wait_for(state='visible', timeout=10000)
                self.logger.info("✓ [STEP 3 COMPLETE] Policyholder form fields visible")
            except Exception as e:
                raise ClaimTitanError(f"Failed at STEP 3 (waiting for policyholder form, specifically input[name='first_name']): {e}")

            # Fill policyholder information
            current_step = "filling policyholder information"
            self.logger.info(f"[STEP 4] Filling policyholder information...")
            try:
                first_name_field.fill(client_data.first_name)
                self.logger.info(f"  ✓ Filled first name: {client_data.first_name}")
                if client_data.last_name:
                    self.page.locator('input[name="last_name"]').fill(client_data.last_name)
                    self.logger.info(f"  ✓ Filled last name: {client_data.last_name}")
                if client_data.phone:
                    self.page.locator('input[name="phone"]').fill(client_data.phone)
                    self.logger.info(f"  ✓ Filled phone: {client_data.phone}")
                if client_data.email:
                    self.page.locator('input[name="email"]').fill(client_data.email)
                    self.logger.info(f"  ✓ Filled email: {client_data.email}")
                self.logger.info("✓ [STEP 4 COMPLETE] Policyholder info filled")
            except Exception as e:
                raise ClaimTitanError(f"Failed at STEP 4 (filling policyholder fields): {e}")

            # Wait for address form fields to be visible (they're shown by default)
            current_step = "waiting for address form fields to appear"
            self.logger.info(f"[STEP 5] Waiting for address form fields...")
            try:
                street_field = self.page.locator('input[name="street"]')
                street_field.wait_for(state='visible', timeout=10000)
                self.logger.info("✓ [STEP 5 COMPLETE] Address form fields visible")
            except Exception as e:
                raise ClaimTitanError(f"Failed at STEP 5 (waiting for address form, specifically input[name='street']): {e}")

            # Fill address information
            current_step = "filling address information"
            self.logger.info(f"[STEP 6] Filling address information...")
            try:
                self.page.locator('input[name="street"]').fill(client_data.street_address)
                self.logger.info(f"  ✓ Filled street: {client_data.street_address}")

                self.page.locator('input[name="city"]').fill(client_data.city)
                self.logger.info(f"  ✓ Filled city: {client_data.city}")

                self.page.locator('select[name="type"]').select_option(client_data.state)  # State dropdown
                self.logger.info(f"  ✓ Selected state: {client_data.state}")

                self.page.locator('input[name="zip"]').fill(client_data.zipcode)
                self.logger.info(f"  ✓ Filled zip: {client_data.zipcode}")

                self.logger.info("✓ [STEP 6 COMPLETE] Address info filled")
            except Exception as e:
                raise ClaimTitanError(f"Failed at STEP 6 (filling address fields): {e}")

            # Fill optional claim information if available
            current_step = "filling optional claim information"
            self.logger.info(f"[STEP 7] Filling optional claim information...")
            try:
                if client_data.claim_number:
                    self.page.locator('input[name="claim_number"]').fill(client_data.claim_number)
                    self.logger.info(f"  ✓ Filled claim number: {client_data.claim_number}")

                if client_data.loss_date:
                    self.page.locator('input[name="loss_date"]').fill(client_data.loss_date)
                    self.logger.info(f"  ✓ Filled loss date: {client_data.loss_date}")

                if client_data.loss_type:
                    # Map loss type to dropdown value (all 33 options)
                    loss_type_mapping = {
                        "fire": "0",
                        "flood": "1",
                        "water": "2",
                        "frozen plumbing": "3",
                        "hail": "4",
                        "wind": "5",
                        "wind / hail": "6",
                        "wind / rain": "7",
                        "windstorm": "8",
                        "tornado": "9",
                        "hurricane": "10",
                        "ice": "11",
                        "smoke": "12",
                        "business interruption": "13",
                        "collapse": "14",
                        "lightning": "15",
                        "theft": "16",
                        "vandalism": "17",
                        "auto": "18",
                        "vehicles": "19",
                        "mold": "20",
                        "ordinance and law": "21",
                        "supplemental": "22",
                        "all risk": "23",
                        "accidental discharge": "24",
                        "soot": "25",
                        "puff back": "26",
                        "roof leak": "27",
                        "tropical storm": "28",
                        "explosion": "29",
                        "plumbing failure": "30",
                        "falling object": "31",
                        "backup": "32",
                    }
                    loss_value = loss_type_mapping.get(client_data.loss_type.lower())
                    if loss_value:
                        self.page.locator('select[name="loss_type"]').select_option(loss_value)
                        self.logger.info(f"  ✓ Selected loss type: {client_data.loss_type}")

                self.logger.info("✓ [STEP 7 COMPLETE] Optional claim info filled")
            except Exception as e:
                raise ClaimTitanError(f"Failed at STEP 7 (filling claim info fields): {e}")

            # Fill insurance company if available (on Insurance tab)
            if client_data.insurance_company:
                current_step = "clicking Insurance tab"
                self.logger.info(f"[STEP 8] Switching to Insurance tab...")
                try:
                    insurance_tab = self.page.locator('button.nav-item:has-text("Insurance")')
                    self._robust_click(insurance_tab, "Insurance tab")
                    self.page.wait_for_timeout(1000)
                    self.logger.info("✓ [STEP 8 COMPLETE] On Insurance tab")
                except Exception as e:
                    raise ClaimTitanError(f"Failed at STEP 8 (clicking Insurance tab, button.nav-item:has-text('Insurance')): {e}")

                # Search for existing insurance company first
                current_step = "searching for insurance company"
                self.logger.info(f"[STEP 9] Searching for insurance company: {client_data.insurance_company}")
                try:
                    search_input = self.page.locator('input[placeholder="Search Providers..."]')
                    search_input.wait_for(state='visible', timeout=10000)
                    search_input.fill(client_data.insurance_company)

                    # Wait for search results to load (debounced 250ms + network)
                    self.page.wait_for_timeout(1500)

                    # Check if any results appeared
                    results_list = self.page.locator('li[x-combobox\\:option]')
                    result_count = results_list.count()

                    if result_count > 0:
                        # Found matches - click on the first one
                        self.logger.info(f"✓ Found {result_count} insurance company match(es)")
                        first_result = results_list.first
                        first_result.click()
                        self.logger.info(f"✓ [STEP 9 COMPLETE] Selected existing insurance company")
                    else:
                        # No results found - check if we need to add new via link or if field is already visible
                        self.logger.info("No existing insurance company found, checking for add new option...")

                        # Clear search box first
                        search_input.clear()
                        self.page.wait_for_timeout(500)

                        # Check if "Add a new provider now" link exists
                        new_insurance_link = self.page.locator('span.text-underline:has-text("Add a new provider now")')
                        if new_insurance_link.is_visible(timeout=2000):
                            self.logger.info("  Found 'Add a new provider now' link, clicking...")
                            self._robust_click(new_insurance_link, "'Add a new provider now' link")
                            self.page.wait_for_timeout(1000)
                        else:
                            self.logger.info("  'Add a new provider now' link not found - field may already be visible")

                        # Fill new insurance company form (field should be visible either way)
                        insurance_name_field = self.page.locator('input[name="insurance_name"]')
                        insurance_name_field.wait_for(state='visible', timeout=5000)
                        insurance_name_field.fill(client_data.insurance_company)
                        self.logger.info(f"  ✓ Filled new insurance company: {client_data.insurance_company}")
                        self.logger.info(f"✓ [STEP 9 COMPLETE] Created new insurance company")

                except Exception as e:
                    raise ClaimTitanError(f"Failed at STEP 9 (searching/adding insurance company): {e}")

            # Submit the form
            current_step = "clicking Save button to submit form"
            self.logger.info(f"[STEP 10] Submitting claim creation form...")
            try:
                submit_button = self.page.locator('button[type="submit"].is-primary:has-text("Save")')
                self._robust_click(submit_button, "Save button")
                self.logger.info("✓ [STEP 10 COMPLETE] Clicked Save button")
            except Exception as e:
                raise ClaimTitanError(f"Failed at STEP 10 (clicking Save button, button[type='submit'].is-primary:has-text('Save')): {e}")

            # Wait for form submission and redirect
            current_step = "waiting for form submission to complete"
            self.logger.info(f"[STEP 11] Waiting for form submission and redirect...")
            try:
                self.page.wait_for_load_state('networkidle', timeout=30000)
                self.page.wait_for_timeout(2000)
                self.logger.info("✓ [STEP 11 COMPLETE] Form submitted, page loaded")
            except Exception as e:
                raise ClaimTitanError(f"Failed at STEP 11 (waiting for form submission to complete): {e}")

            # Get the URL of the created claim
            claim_url = self.page.url

            self.logger.info(f"✓ Successfully created claim for {client_name}")
            self.logger.info(f"✓ Claim URL: {claim_url}")

            return ClaimCreationResult(
                client_name=client_name,
                claim_url=claim_url,
                success=True,
                timestamp=datetime.now()
            )

        except ClaimTitanError as e:
            # Already has detailed error message
            screenshot_path = self._take_screenshot(f"claim_creation_{client_data.first_name}")
            self.logger.error("="*80)
            self.logger.error(f"CLAIM CREATION FAILED!")
            self.logger.error(f"Failed at: {current_step}")
            self.logger.error(f"Error: {e}")
            self.logger.error(f"Screenshot: {screenshot_path}")
            self.logger.error("="*80)

            return ClaimCreationResult(
                client_name=client_name,
                claim_url=None,
                success=False,
                timestamp=datetime.now(),
                error_message=f"Failed at: {current_step}. Error: {str(e)}",
                screenshot_path=screenshot_path
            )

        except Exception as e:
            # Unexpected error
            screenshot_path = self._take_screenshot(f"claim_creation_{client_data.first_name}")
            self.logger.error("="*80)
            self.logger.error(f"CLAIM CREATION FAILED WITH UNEXPECTED ERROR!")
            self.logger.error(f"Failed at: {current_step}")
            self.logger.error(f"Error type: {type(e).__name__}")
            self.logger.error(f"Error: {e}")
            self.logger.error(f"Screenshot: {screenshot_path}")
            self.logger.error("="*80)

            return ClaimCreationResult(
                client_name=client_name,
                claim_url=None,
                success=False,
                timestamp=datetime.now(),
                error_message=f"Failed at: {current_step}. Unexpected error: {str(e)}",
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
        """Open notes sidebar and add note form with robust timeout handling."""
        self.logger.info("Opening notes form...")

        max_retries = 3
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    self.logger.info(f"Retry attempt {attempt + 1}/{max_retries}...")

                # Step 0: Wait for page to be fully loaded and interactive
                self.logger.info("Waiting for page to be fully loaded...")
                self.page.wait_for_load_state('networkidle', timeout=60000)
                self.page.wait_for_load_state('domcontentloaded', timeout=60000)
                self.logger.info("✓ Page fully loaded")

                # Additional wait for any animations/JavaScript to settle
                self.page.wait_for_timeout(1000)

                # Step 1: Click Notes sidebar button to open notes panel
                self.logger.info("Looking for Notes sidebar button...")
                notes_sidebar_button = self.page.locator('button.sidebar-nav-item:has-text("Notes")')

                # Wait for button to be visible with extended timeout
                notes_sidebar_button.wait_for(state='visible', timeout=60000)
                self.logger.info("✓ Notes button found and visible")

                # Scroll element into view to ensure it's clickable
                self.logger.info("Scrolling Notes button into view...")
                notes_sidebar_button.scroll_into_view_if_needed(timeout=10000)
                self.page.wait_for_timeout(500)

                # Try clicking with multiple strategies
                click_success = False

                # Strategy 1: Normal click
                try:
                    self.logger.info("Attempting normal click on Notes button...")
                    notes_sidebar_button.click(timeout=10000)
                    click_success = True
                    self.logger.info("✓ Normal click succeeded")
                except Exception as e:
                    self.logger.warning(f"Normal click failed: {e}")

                # Strategy 2: Force click (if normal click failed)
                if not click_success:
                    try:
                        self.logger.info("Attempting force click on Notes button...")
                        notes_sidebar_button.click(force=True, timeout=10000)
                        click_success = True
                        self.logger.info("✓ Force click succeeded")
                    except Exception as e:
                        self.logger.warning(f"Force click failed: {e}")

                # Strategy 3: JavaScript click (if force click failed)
                if not click_success:
                    try:
                        self.logger.info("Attempting JavaScript click on Notes button...")
                        self.page.evaluate("document.querySelector('button.sidebar-nav-item:has-text(\"Notes\")').click()")
                        click_success = True
                        self.logger.info("✓ JavaScript click succeeded")
                    except Exception as e:
                        self.logger.warning(f"JavaScript click failed: {e}")

                if not click_success:
                    raise PostError("All click strategies failed for Notes button")

                # Wait for sidebar to fully render and verify it opened
                self.logger.info("Waiting for notes panel to render...")
                self.page.wait_for_timeout(2000)

                # Verify the notes panel actually opened by checking for "New Note" button
                self.logger.info("Verifying notes panel opened...")
                new_note_button = self.page.locator('a.button:has-text("New Note")')
                new_note_button.wait_for(state='visible', timeout=10000)
                self.logger.info("✓ Notes panel confirmed open")

                # Step 2: Click "New Note" button inside the notes panel
                self.logger.info("Scrolling New Note button into view...")
                new_note_button.scroll_into_view_if_needed(timeout=10000)
                self.page.wait_for_timeout(500)

                # Try clicking New Note button with multiple strategies
                click_success = False

                try:
                    self.logger.info("Attempting normal click on New Note button...")
                    new_note_button.click(timeout=10000)
                    click_success = True
                    self.logger.info("✓ Clicked New Note button")
                except Exception as e:
                    self.logger.warning(f"Normal click on New Note failed: {e}")
                    try:
                        self.logger.info("Attempting force click on New Note button...")
                        new_note_button.click(force=True, timeout=10000)
                        click_success = True
                        self.logger.info("✓ Force clicked New Note button")
                    except Exception as e2:
                        self.logger.error(f"Force click on New Note also failed: {e2}")
                        raise PostError(f"Failed to click New Note button: {e2}")

                # Wait for note form to appear (with extended timeout)
                self.logger.info("Waiting for note form to appear...")
                self.page.wait_for_selector(
                    'form[action*="/notes"] input[name="title"]',
                    state='visible',
                    timeout=60000
                )

                self.logger.info("✓ Notes form opened successfully")
                return  # Success!

            except Exception as e:
                error_msg = f"Attempt {attempt + 1} failed: {e}"
                self.logger.error(error_msg)

                if attempt < max_retries - 1:
                    self.logger.info("Will retry after brief wait...")
                    self.page.wait_for_timeout(3000)
                else:
                    # Final failure - take screenshot and raise
                    self.logger.error("All retry attempts exhausted")
                    raise PostError(f"Failed to open notes form after {max_retries} attempts: {e}")

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
            # Get the notes form specifically (not expense or other forms)
            notes_form = self.page.locator('form[action*="/notes"]')

            # Fill fields within the notes form
            notes_form.locator('input[name="title"]').fill(title)
            notes_form.locator('textarea[name="description"]').fill(description)

            self.logger.info("Submitting note...")

            # Find and click the "Save Note" button explicitly
            save_button = notes_form.locator('button:has-text("Save Note")')

            # Ensure button is visible and clickable
            save_button.wait_for(state='visible', timeout=5000)
            save_button.click()

            self.logger.info("Clicked Save Note button")

            # Wait a moment for the note to be saved
            # The form submission is AJAX-based and may not trigger navigation
            self.page.wait_for_timeout(2000)

            self.logger.info("✓ Note submitted")

        except Exception as e:
            raise PostError(f"Failed to fill/submit note form: {e}")

    def _robust_click(self, locator, element_name: str, timeout: int = 10000):
        """
        Try multiple strategies to click an element robustly.

        Args:
            locator: Playwright locator object
            element_name: Name of element for logging
            timeout: Timeout in milliseconds

        Raises:
            BrowserError: If all click strategies fail
        """
        self.logger.info(f"  Attempting to click {element_name}...")

        # Wait for element to be visible
        try:
            locator.wait_for(state='visible', timeout=timeout)
            self.logger.info(f"  ✓ Element {element_name} is visible")
        except Exception as e:
            raise BrowserError(f"Element {element_name} never became visible after {timeout}ms: {e}")

        # Scroll into view
        try:
            locator.scroll_into_view_if_needed(timeout=timeout)
            self.page.wait_for_timeout(300)
            self.logger.info(f"  ✓ Element {element_name} scrolled into view")
        except Exception as e:
            self.logger.warning(f"  Could not scroll {element_name} into view: {e}")

        # Try different click strategies
        strategies = [
            ("normal click", lambda: locator.click(timeout=timeout)),
            ("force click", lambda: locator.click(force=True, timeout=timeout)),
            ("JavaScript click", lambda: locator.evaluate("el => el.click()"))
        ]

        last_error = None
        for strategy_name, click_fn in strategies:
            try:
                self.logger.info(f"  Trying {strategy_name} on {element_name}...")
                click_fn()
                self.logger.info(f"  ✓ {strategy_name} succeeded on {element_name}")
                return  # Success!
            except Exception as e:
                self.logger.warning(f"  {strategy_name} failed on {element_name}: {e}")
                last_error = e
                continue

        # All strategies failed
        raise BrowserError(f"All click strategies failed for {element_name}. Last error: {last_error}")

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

    def scrape_document_folders(self) -> List[str]:
        """
        Scrape available document folder names from the current claim page.

        Returns:
            List of folder names available for this claim

        Raises:
            PostError: If unable to scrape folders
        """
        self.logger.info("Scraping document folder names...")

        try:
            # Step 1: Click the Files tab to navigate to files section
            files_tab = self.page.locator('a.nav-item:has-text("Files")')

            if not files_tab.is_visible():
                # Try alternative selector with href
                files_tab = self.page.locator('a[href*="/files"]').first

            files_tab.click()
            self.logger.info("Clicked Files tab")

            # Wait for page to load
            self.page.wait_for_load_state('networkidle')

            # Wait for folder cards to appear
            self.page.wait_for_selector('section.column-12', state='visible', timeout=10000)

            # Step 2: Find all folder name elements
            # Folders are in <p class="text-primary hover:text-underline font-bold ...">
            folder_elements = self.page.locator('p.text-primary.hover\\:text-underline.font-bold')

            # Step 3: Extract text from each folder element
            folders = []
            count = folder_elements.count()

            for i in range(count):
                folder_name = folder_elements.nth(i).inner_text().strip()
                if folder_name:  # Skip empty folder names
                    folders.append(folder_name)

            if not folders:
                self.logger.warning("No document folders found on Files page")
                # Return a default fallback
                folders = ["Other"]

            self.logger.info(f"✓ Found {len(folders)} folder(s): {folders}")
            return folders

        except Exception as e:
            self.logger.error(f"Failed to scrape document folders: {e}")
            # Take screenshot for debugging
            screenshot_path = self._take_screenshot(f"folder_scrape_failed")
            self.logger.error(f"Screenshot saved: {screenshot_path}")
            raise PostError(f"Failed to scrape document folders: {e}")

    def upload_attachments(
        self,
        attachments: List[AttachmentData],
        claim_number: str,
        email_summary: str
    ) -> Dict[str, str]:
        """
        Upload attachments to Claim Titan with AI-powered folder matching.

        Args:
            attachments: List of attachment data objects
            claim_number: Claim number
            email_summary: Email summary for context

        Returns:
            Dictionary mapping filename to folder name (or "Failed" if upload failed)
        """
        if not attachments:
            self.logger.info("No attachments to upload")
            return {}

        self.logger.info(f"Processing {len(attachments)} attachment(s) for upload...")

        # Scrape available folders
        try:
            available_folders = self.scrape_document_folders()
        except Exception as e:
            self.logger.error(f"Failed to scrape folders: {e}")
            return {att.filename: "Failed" for att in attachments}

        # Use AI to match attachments to folders
        matches = self.attachment_handler.match_attachments_to_folders(
            attachments=attachments,
            available_folders=available_folders,
            email_summary=email_summary
        )

        if not matches:
            self.logger.error("Failed to match attachments to folders")
            return {att.filename: "Failed" for att in attachments}

        # Upload each file (or log in test mode)
        results = {}
        for attachment in attachments:
            filename = attachment.filename
            folder = matches.get(filename)

            if not folder:
                self.logger.error(f"No folder match for {filename}, skipping")
                results[filename] = "Failed"
                continue

            try:
                if Config.UPLOAD_ATTACHMENTS_TO_CRM:
                    # Actually upload the file
                    success = self._upload_file_to_folder(
                        attachment=attachment,
                        folder_name=folder
                    )

                    if success:
                        self.logger.info(f"✓ Uploaded {filename} to folder: {folder}")
                        results[filename] = folder
                    else:
                        self.logger.error(f"✗ Failed to upload {filename}")
                        results[filename] = "Failed"
                else:
                    # Test mode - just log what would happen
                    self.logger.info(f"[TEST MODE] Would upload {filename} to folder: {folder}")
                    results[filename] = folder  # Return folder name in test mode

            except Exception as e:
                self.logger.error(f"Error uploading {filename}: {e}")
                results[filename] = "Failed"

        return results

    def _upload_file_to_folder(
        self,
        attachment: AttachmentData,
        folder_name: str
    ) -> bool:
        """
        Upload a single file to a specific folder in Claim Titan.

        Args:
            attachment: Attachment data
            folder_name: Target folder name

        Returns:
            True if upload successful, False otherwise
        """
        self.logger.info(f"Uploading {attachment.filename} to {folder_name}...")

        try:
            # Navigate to documents section if needed
            # This depends on where we are in the UI

            # Click on the target folder
            # folder_button = self.page.locator(f'button:has-text("{folder_name}")').first
            # folder_button.click()

            # Find file input element
            # file_input = self.page.locator('input[type="file"]')
            # file_input.set_files(attachment.file_path)

            # Wait for upload to complete
            # self.page.wait_for_selector('.upload-success', timeout=10000)

            # TODO: Implement actual upload logic based on Claim Titan UI
            # For now, return False to indicate not implemented
            self.logger.warning("Upload logic not yet implemented - needs UI inspection")
            return False

        except Exception as e:
            self.logger.error(f"Upload failed for {attachment.filename}: {e}")
            screenshot_path = self._take_screenshot(f"upload_failed_{attachment.filename}")
            self.logger.error(f"Screenshot saved: {screenshot_path}")
            return False


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
