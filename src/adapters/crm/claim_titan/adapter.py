"""
Claim Titan CRM Adapter for Forerunner Claims Automation.
Manages browser connection, login, and claim search functionality.
Features (like comments, contract addition) are loaded as separate modules.
"""

import logging
from typing import Optional, List, Dict
from playwright.sync_api import sync_playwright, Browser, Page, Playwright

from config import Config
from attachment_handler import AttachmentHandler

# Import exceptions
from .exceptions import ClaimTitanError, LoginError, SearchError, PostError, BrowserError

# Import features (imported after exceptions to avoid circular imports)
from .features.comments import CommentsFeature
from .features.contract_addition import ContractAdditionFeature
from .features.check_deposit import CheckDepositFeature


class ClaimTitanAdapter:
    """
    Claim Titan CRM adapter.
    Manages browser automation, authentication, and claim search.
    Features are loaded as pluggable modules.
    """

    def __init__(self,
                 username: Optional[str] = None,
                 password: Optional[str] = None,
                 base_url: Optional[str] = None,
                 headless: Optional[bool] = None,
                 config: Optional[object] = None):
        """
        Initialize the Claim Titan adapter.

        Args:
            username: Claim Titan username (defaults to Config.CLAIM_TITAN_USER)
            password: Claim Titan password (defaults to Config.CLAIM_TITAN_PASS)
            base_url: Claim Titan URL (defaults to Config.CLAIM_TITAN_URL)
            headless: Run browser in headless mode (defaults to Config.BROWSER_HEADLESS)
            config: Config object (defaults to Config class)
        """
        self.config = config or Config
        self.username = username or self.config.CLAIM_TITAN_USER
        self.password = password or self.config.CLAIM_TITAN_PASS
        self.base_url = base_url or self.config.CLAIM_TITAN_URL
        self.headless = headless if headless is not None else self.config.BROWSER_HEADLESS

        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.logger = logging.getLogger(__name__)

        if not self.username or not self.password:
            raise ValueError("Claim Titan credentials not configured in .env file")

        # Attachment handler for file operations
        self.attachment_handler = AttachmentHandler()

        # Features dictionary (loaded based on config)
        self.features = {}
        self._load_features()

        self.logger.info("ClaimTitanAdapter initialized")

    def _load_features(self):
        """Load enabled features based on configuration."""
        # Comments feature (with attachment upload toggle)
        if getattr(self.config, 'FEATURE_COMMENTS_ENABLED', True):
            upload_attachments = getattr(self.config, 'COMMENTS_UPLOAD_ATTACHMENTS', False)
            self.features['comments'] = CommentsFeature(
                adapter=self,
                upload_attachments=upload_attachments
            )
            self.logger.info(f"Loaded CommentsFeature (upload_attachments={upload_attachments})")

        # Contract addition feature
        if getattr(self.config, 'FEATURE_CONTRACT_ADDITION_ENABLED', True):
            self.features['contract_addition'] = ContractAdditionFeature(adapter=self)
            self.logger.info("Loaded ContractAdditionFeature")

        # Check deposit feature
        if getattr(self.config, 'FEATURE_CHECK_DEPOSIT_ENABLED', True):
            self.features['check_deposit'] = CheckDepositFeature(adapter=self)
            self.logger.info("Loaded CheckDepositFeature")

    def get_feature(self, feature_name: str):
        """
        Get a loaded feature by name.

        Args:
            feature_name: Name of the feature ('comments', 'contract_addition', etc.)

        Returns:
            Feature instance or None if not loaded
        """
        return self.features.get(feature_name)

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
            launch_args = []
            if self.headless:
                # Only use these args in headless mode
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

            # Login with retry logic
            login_attempts = 3
            login_successful = False

            for attempt in range(login_attempts):
                try:
                    self.logger.info(f"DEBUG: Login attempt {attempt + 1}/{login_attempts}...")
                    self._login()
                    login_successful = True
                    break

                except LoginError as e:
                    if attempt < login_attempts - 1:
                        wait_time = 5 * (2 ** attempt)
                        self.logger.warning(f"Login attempt {attempt + 1} failed: {e}")
                        self.logger.info(f"Retrying login in {wait_time} seconds...")
                        import time
                        time.sleep(wait_time)
                    else:
                        raise

            if not login_successful:
                raise BrowserError("Login failed after multiple attempts")

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
            self.page.wait_for_load_state('load')
            self.page.wait_for_timeout(1000)

            # Verify login success
            if not self.page.locator('input[name="search"]').is_visible():
                raise LoginError("Login failed - search box not found on dashboard")

            self.logger.info("✓ Login successful")

        except LoginError:
            raise
        except Exception as e:
            raise LoginError(f"Login failed: {e}")

    def search_claim(self, claim_number: str) -> str:
        """
        Search for a claim by number with retry logic.
        Tries multiple variations: original, without suffix, without hyphens.

        Args:
            claim_number: Claim number to search for

        Returns:
            The claim number format that found results

        Raises:
            SearchError: If claim not found after retries
        """
        self.logger.info(f"Searching for claim: {claim_number}")

        # Ensure we're on the Claims page
        current_url = self.page.url
        if "/claims" not in current_url:
            self.logger.info(f"  Not on Claims page (URL: {current_url}), navigating...")
            self.page.goto("https://claimtitan.com/claims")
            self.page.wait_for_load_state('load', timeout=30000)
            self.page.wait_for_timeout(2000)

        # Find the search box
        self.logger.info(f"  Looking for search box...")
        search_box = None
        for i in range(3):
            try:
                search_box = self.page.get_by_placeholder("Search by Claim Number, Job")
                search_box.wait_for(state='visible', timeout=10000)
                self.logger.info(f"  ✓ Found search box")
                break
            except Exception as e:
                if i < 2:
                    self.logger.warning(f"  Search box not found (attempt {i+1}/3), retrying...")
                    self.page.wait_for_timeout(2000)
                else:
                    raise SearchError(f"Search box not found after 3 attempts. URL: {self.page.url}. Error: {e}")

        # Build list of variations to try (most specific first)
        variations = [claim_number]

        if '-' in claim_number:
            # Try base number before first hyphen (e.g., "7008533516-1-3" -> "7008533516")
            base = claim_number.split('-', 1)[0]
            if base not in variations:
                variations.append(base)
            # Try without hyphens (e.g., "01-009-240484" -> "01009240484")
            variations.append(claim_number.replace('-', ''))

        # Filter out variations that have no digits or are too short to be useful
        variations = [v for v in variations if any(c.isdigit() for c in v) and len(v) >= 5]

        self.logger.info(f"  Will try {len(variations)} variation(s): {variations}")

        # RETRY LOGIC: Claim might be indexing
        max_retries = 2
        retry_delay = 30

        for attempt in range(max_retries):
            if attempt > 0:
                self.logger.info(f"  Retry attempt {attempt + 1}/{max_retries} after {retry_delay}s delay...")
                import time
                time.sleep(retry_delay)

            # Try each variation
            for variation in variations:
                self.logger.info(f"  Trying variation: {variation}")
                search_box.clear()
                search_box.fill(variation)
                self.page.wait_for_timeout(500)
                self.logger.info(f"  Pressing Enter...")
                search_box.press('Enter')
                self.page.wait_for_load_state('load', timeout=30000)

                self.logger.info(f"  Waiting for search results...")
                self.page.wait_for_timeout(3000)

                self.logger.info(f"  Checking for results with variation '{variation}'...")
                if self._has_claim_results():
                    self.logger.info(f"  Found results, verifying clickable link exists...")
                    try:
                        # When using a shorter variation, try matching rows by the original claim number first
                        # to avoid clicking a different claim that shares the same prefix
                        row_match_targets = [variation]
                        if variation != claim_number:
                            row_match_targets = [claim_number, variation]
                            self.logger.info(f"  Short variation used for search, will try row match by original '{claim_number}' first")

                        for row_target in row_match_targets:
                            matching_rows = self.page.locator(f'div.columns:has(span:has-text("{row_target}"))')
                            row_count = matching_rows.count()
                            self.logger.info(f"  Found {row_count} row(s) matching '{row_target}'")

                            for row_idx in range(row_count):
                                claim_row = matching_rows.nth(row_idx)
                                if not claim_row.is_visible(timeout=2000):
                                    continue

                                all_links = claim_row.locator('a')
                                link_count = all_links.count()

                                for i in range(link_count):
                                    link = all_links.nth(i)
                                    href = link.get_attribute('href')
                                    if href and '/claims/' in href and not any(x in href for x in ['/board', '/jobs', '?']):
                                        claim_id = href.split('/claims/')[-1]
                                        if claim_id.isdigit():
                                            found_format = row_target if row_target == variation else variation
                                            if attempt > 0:
                                                self.logger.info(f"✓ Found clickable claim with format: {found_format} (row matched '{row_target}', after {attempt + 1} attempts)")
                                            else:
                                                self.logger.info(f"✓ Found clickable claim with format: {found_format} (row matched '{row_target}')")
                                            return row_target

                            self.logger.info(f"  No valid claim link in rows matching '{row_target}', trying next...")

                        self.logger.info(f"  Found results for '{variation}' but no valid claim link in any row, trying next...")
                    except Exception as e:
                        self.logger.info(f"  Error checking link for '{variation}': {e}, trying next...")
                else:
                    self.logger.info(f"  No results for variation '{variation}', trying next...")

            if attempt < max_retries - 1:
                self.logger.warning(f"  Claim {claim_number} not found with any variation (attempt {attempt + 1}), will retry...")

        raise SearchError(f"Claim {claim_number} not found after {max_retries} attempts (tried variations: {variations})")

    def _has_claim_results(self) -> bool:
        """Check if search returned any claim results."""
        try:
            self.page.wait_for_timeout(1000)

            # Check if claim was auto-opened
            claim_info = self.page.locator('h4:has-text("Claim Information")').first
            if claim_info.is_visible(timeout=1000):
                self.logger.info(f"    ✓ Claim auto-opened - on claim detail page")
                return True

            # Check if on search results page
            claim_links = self.page.locator('a[href*="/claims/"]')
            if claim_links.count() > 0:
                self.logger.info(f"    ✓ Found {claim_links.count()} claim(s) in search results")
                return True

            # Check URL
            current_url = self.page.url
            if '/claims/' in current_url and current_url != 'https://claimtitan.com/claims':
                self.logger.info(f"    ✓ On claim page (URL: {current_url})")
                return True

            self.logger.info(f"    ✗ No results found (URL: {current_url})")
            return False

        except Exception as e:
            self.logger.info(f"    ✗ Error checking for results: {e}")
            return False

    def open_claim(self, claim_number: str, original_claim: str):
        """
        Click on claim in search results and verify we're on the right claim.

        Args:
            claim_number: The claim number format that found results
            original_claim: The original claim number from the email
        """
        self.logger.info(f"Opening claim: {claim_number}")

        claim_row = self.page.locator(f'div.columns:has(span:has-text("{claim_number}"))').first

        try:
            claim_row.wait_for(state='visible', timeout=10000)
            self.logger.info(f"  ✓ Found claim row")
        except Exception:
            raise SearchError(f"Could not find row with claim {claim_number}")

        self.logger.info(f"  Looking for link inside claim row...")
        all_links = claim_row.locator('a')
        link_count = all_links.count()
        self.logger.info(f"  Found {link_count} total link(s) in row")

        claim_link = None
        for i in range(link_count):
            link = all_links.nth(i)
            href = link.get_attribute('href')
            self.logger.info(f"    Link {i}: href='{href}'")

            if href and '/claims/' in href and not any(x in href for x in ['/board', '/jobs', '?']):
                claim_id = href.split('/claims/')[-1]
                if claim_id.isdigit():
                    self.logger.info(f"    ✓ This is the claim link (ID: {claim_id})")
                    claim_link = link
                    break
                else:
                    self.logger.info(f"    ✗ Not a claim detail link")

        if not claim_link:
            raise SearchError(f"No clickable claim detail link found in row for {claim_number}")

        try:
            link_text = claim_link.inner_text(timeout=2000)
            link_href = claim_link.get_attribute('href')
            self.logger.info(f"  ✓ Found claim link: '{link_text}' (href: {link_href})")
        except Exception as e:
            self.logger.info(f"  Link found but couldn't get text: {e}")

        self.logger.info(f"  Scrolling to claim link and clicking...")
        try:
            claim_link.scroll_into_view_if_needed()
            self.page.wait_for_timeout(500)
            claim_link.click(force=True)
            self.logger.info(f"  ✓ Clicked claim link")
        except Exception as e:
            raise SearchError(f"Could not click claim link: {e}")

        self.page.wait_for_load_state('load')
        self.page.wait_for_timeout(1000)

        # Verify we're on the correct claim
        self.verify_claim_number(original_claim)

        self.logger.info(f"✓ Opened claim page")

    def verify_claim_number(self, expected_claim: str):
        """
        Verify we're on the correct claim page.

        Args:
            expected_claim: The claim number we expect to see
        """
        self.logger.info(f"Verifying claim number: {expected_claim}")

        try:
            claim_label = self.page.locator('p.text-grey-light.text-xs:has-text("Claim Number")')
            flex_container = claim_label.locator('xpath=..')
            claim_number_element = flex_container.locator('p.text-grey.font-500').first

            try:
                claim_number_element.wait_for(state='visible', timeout=30000)
            except Exception:
                raise PostError("Cannot verify claim number - element not found on page")

            page_claim_number = claim_number_element.inner_text().strip()

            normalized_expected = expected_claim.replace('-', '').upper()
            normalized_page = page_claim_number.replace('-', '').upper()

            if normalized_expected != normalized_page:
                if not (normalized_expected.startswith(normalized_page) or
                        normalized_page.startswith(normalized_expected)):
                    raise PostError(
                        f"Claim number mismatch! Expected: {expected_claim}, "
                        f"Found on page: {page_claim_number}"
                    )
                self.logger.info(f"  Claim number matches with suffix difference: '{expected_claim}' vs '{page_claim_number}'")

            self.logger.info(f"✓ Verified claim number: {page_claim_number}")

        except PostError:
            raise
        except Exception as e:
            raise PostError(f"Failed to verify claim number: {e}")

    def robust_click(self, locator, element_name: str, timeout: int = 10000):
        """
        Try multiple strategies to click an element robustly.

        Args:
            locator: Playwright locator object
            element_name: Name of element for logging
            timeout: Timeout in milliseconds
        """
        self.logger.info(f"  Attempting to click {element_name}...")

        try:
            locator.wait_for(state='visible', timeout=timeout)
            self.logger.info(f"  ✓ Element {element_name} is visible")
        except Exception as e:
            raise BrowserError(f"Element {element_name} never became visible after {timeout}ms: {e}")

        try:
            locator.scroll_into_view_if_needed(timeout=timeout)
            self.page.wait_for_timeout(300)
            self.logger.info(f"  ✓ Element {element_name} scrolled into view")
        except Exception as e:
            self.logger.warning(f"  Could not scroll {element_name} into view: {e}")

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
                return
            except Exception as e:
                self.logger.warning(f"  {strategy_name} failed on {element_name}: {e}")
                last_error = e
                continue

        raise BrowserError(f"All click strategies failed for {element_name}. Last error: {last_error}")

    def take_screenshot(self, claim_number: str) -> str:
        """Take screenshot on error for debugging."""
        try:
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
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
        """
        self.logger.info("Scraping document folder names...")

        try:
            files_tab = self.page.locator('a.nav-item:has-text("Files")')

            if not files_tab.is_visible():
                files_tab = self.page.locator('a[href*="/files"]').first

            files_tab.click()
            self.logger.info("Clicked Files tab")

            self.page.wait_for_load_state('load')
            self.page.wait_for_timeout(1000)
            self.page.wait_for_selector('section.column-12', state='visible', timeout=10000)

            folder_elements = self.page.locator('p.text-primary.hover\\:text-underline.font-bold')

            folders = []
            count = folder_elements.count()

            for i in range(count):
                folder_name = folder_elements.nth(i).inner_text().strip()
                if folder_name:
                    folders.append(folder_name)

            if not folders:
                self.logger.warning("No document folders found on Files page")
                folders = ["Other"]

            self.logger.info(f"✓ Found {len(folders)} folder(s): {folders}")
            return folders

        except Exception as e:
            self.logger.error(f"Failed to scrape document folders: {e}")
            screenshot_path = self.take_screenshot(f"folder_scrape_failed")
            self.logger.error(f"Screenshot saved: {screenshot_path}")
            raise PostError(f"Failed to scrape document folders: {e}")
