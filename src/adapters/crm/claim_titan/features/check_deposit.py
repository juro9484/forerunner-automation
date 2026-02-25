"""
Check Deposit Feature for ClaimTitan.
Navigates to claim, adds carrier check with extracted data.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from playwright.sync_api import Page

from ..exceptions import NavigationError, FormSubmissionError
from check_parser import CheckData


@dataclass
class ClaimTitanResult:
    """Result of adding a check to ClaimTitan."""
    claim_number: str
    note_title: str
    note_description: str
    success: bool
    timestamp: datetime
    claim_url: Optional[str] = None
    error_message: Optional[str] = None
    screenshot_path: Optional[str] = None


class CheckDepositFeature:
    """
    Adds carrier checks to ClaimTitan claims.
    Navigates: claim → Accounting → Carrier Checks → Add Check form
    """

    def __init__(self, adapter):
        """
        Initialize check deposit feature.

        Args:
            adapter: ClaimTitanAdapter instance
        """
        self.adapter = adapter
        self.config = adapter.config
        self.logger = logging.getLogger(__name__)

    def process(self, check_data: CheckData, check_pdf_path) -> ClaimTitanResult:
        """
        Add a carrier check to ClaimTitan.

        Args:
            check_data: Extracted check data
            check_pdf_path: Path to original check PDF (for upload)

        Returns:
            ClaimTitanResult with success/failure status
        """
        try:
            self.logger.info(f"Adding carrier check to claim {check_data.claim_number}")
            self.logger.info(f"  Amount: {check_data.check_amount}")
            self.logger.info(f"  Check #: {check_data.check_number}")
            self.logger.info(f"  Confidence: {check_data.overall_confidence}%")

            # Navigate to carrier checks page
            claim_url = self._navigate_to_carrier_checks(check_data.claim_number)

            # Click "Add Check" button
            self._click_add_check_button()

            # Fill the form
            self._fill_check_form(check_data, check_pdf_path)

            # Submit form
            self._submit_form()

            self.logger.info(f"✓ Successfully added carrier check to claim {check_data.claim_number}")

            return ClaimTitanResult(
                claim_number=check_data.claim_number,
                note_title=f"Carrier Check - ${check_data.check_amount}",
                note_description=f"Check #{check_data.check_number} from {check_data.payer}",
                success=True,
                timestamp=datetime.now(),
                error_message=None,
                screenshot_path=None,
                claim_url=claim_url
            )

        except Exception as e:
            error_msg = f"Failed to add carrier check: {str(e)}"
            self.logger.error(error_msg, exc_info=True)

            # Take screenshot for debugging
            screenshot_path = None
            try:
                screenshot_dir = self.config.SCREENSHOTS_DIR
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                screenshot_path = screenshot_dir / f"check_deposit_error_{check_data.claim_number}_{timestamp}.png"
                self.adapter.page.screenshot(path=str(screenshot_path))
                self.logger.info(f"Error screenshot saved: {screenshot_path}")
            except Exception:
                pass

            return ClaimTitanResult(
                claim_number=check_data.claim_number,
                note_title=f"Carrier Check - ${check_data.check_amount}",
                note_description=f"Check #{check_data.check_number} from {check_data.payer}",
                success=False,
                timestamp=datetime.now(),
                error_message=error_msg,
                screenshot_path=screenshot_path
            )

    def _navigate_to_carrier_checks(self, claim_number: str) -> str:
        """
        Navigate to the Carrier Checks page for a claim.

        Args:
            claim_number: Claim number to navigate to

        Returns:
            Claim URL

        Raises:
            NavigationError: If navigation fails
        """
        try:
            # Navigate to claims list page first (in case we're on a different claim)
            current_url = self.adapter.page.url
            if '/claims/' in current_url and current_url != 'https://claimtitan.com/claims':
                self.logger.info(f"  Currently on specific claim page, navigating to claims list...")
                self.adapter.page.goto('https://claimtitan.com/claims')
                self.adapter.page.wait_for_load_state('load', timeout=30000)
                self.adapter.page.wait_for_timeout(2000)

            # Search for claim with robust retry logic
            found_variation = self.adapter.search_claim(claim_number)
            self.logger.info(f"  Found claim with variation: {found_variation}")

            # Open the claim if not already on it
            if '/claims/' not in self.adapter.page.url or self.adapter.page.url == 'https://claimtitan.com/claims':
                self.adapter.open_claim(found_variation, claim_number)
                self.logger.info(f"  Opened claim page")

            # Get the claim URL
            claim_url = self.adapter.page.url
            self.logger.info(f"  On claim overview: {claim_url}")

            # Click Accounting tab
            self.logger.info(f"  Clicking Accounting tab...")
            accounting_link = self.adapter.page.locator('a[href*="/worksheet"]:has-text("Accounting")').first
            accounting_link.wait_for(state='visible', timeout=10000)
            accounting_link.click()
            self.adapter.page.wait_for_load_state('load', timeout=30000)
            self.adapter.page.wait_for_timeout(2000)

            self.logger.info(f"  ✓ On Accounting page")

            # Click Carrier Checks sub-tab
            self.logger.info(f"  Clicking Carrier Checks tab...")
            carrier_checks_link = self.adapter.page.locator('a[href*="/payment"]:has-text("Carrier")').first
            carrier_checks_link.wait_for(state='visible', timeout=10000)
            carrier_checks_link.click()
            self.adapter.page.wait_for_load_state('load', timeout=30000)
            self.adapter.page.wait_for_timeout(2000)

            self.logger.info(f"  ✓ On Carrier Checks page")

            return claim_url

        except Exception as e:
            raise NavigationError(f"Failed to navigate to Carrier Checks page: {e}")

    def _click_add_check_button(self):
        """Click the 'Add Check' button to open the form slideover."""
        try:
            self.logger.info(f"  Clicking 'Add Check' button...")

            # Find and click the Add Check button
            add_button = self.adapter.page.locator('button:has-text("Add")').first
            add_button.wait_for(state='visible', timeout=10000)
            add_button.click()

            # Wait for slideover to open
            self.adapter.page.wait_for_timeout(2000)

            # Verify slideover and Save button are visible
            save_button = self.adapter.page.locator('button[type="submit"]:has-text("Save")').first
            save_button.wait_for(state='visible', timeout=10000)

            self.logger.info(f"  ✓ Add Check slideover opened")

        except Exception as e:
            raise NavigationError(f"Failed to open Add Check form: {e}")

    def _fill_livewire_field(self, locator, value, field_name):
        """
        Fill a Livewire wire:model field and dispatch proper events.

        Args:
            locator: Playwright locator
            value: Value to fill
            field_name: Field name for logging
        """
        # Type the value character by character (simulates real typing)
        locator.click()
        self.adapter.page.wait_for_timeout(100)
        locator.fill('')  # Clear first
        locator.type(str(value), delay=10)  # Type with 10ms delay between chars
        self.adapter.page.wait_for_timeout(100)

        self.logger.info(f"    ✓ {field_name}: {value}")

    def _fill_check_form(self, check_data: CheckData, check_pdf_path: Path):
        """
        Fill out the carrier check form.

        Args:
            check_data: Extracted check data
            check_pdf_path: Path to check PDF for upload
        """
        try:
            self.logger.info(f"  Filling check form...")

            # Amount
            amount_input = self.adapter.page.locator('input[wire\\:model="form.amount"]').first
            amount_input.wait_for(state='visible', timeout=10000)
            self._fill_livewire_field(amount_input, check_data.check_amount, "Amount")

            # Check Number (Reference ID)
            ref_input = self.adapter.page.locator('input[wire\\:model="form.reference_id"]').first
            self._fill_livewire_field(ref_input, check_data.check_number, "Check #")

            # Payment Name (use payer)
            name_input = self.adapter.page.locator('input[wire\\:model="form.name"]').first
            self._fill_livewire_field(name_input, check_data.payer, "Payment Name")

            # Notes (include insured name and confidence info)
            notes_text = f"Insured: {check_data.insured_name}\nAuto-extracted with {check_data.overall_confidence}% confidence"
            if check_data.notes and check_data.notes != "No issues":
                notes_text += f"\nNotes: {check_data.notes}"

            notes_textarea = self.adapter.page.locator('textarea[wire\\:model="form.notes"]').first
            self._fill_livewire_field(notes_textarea, notes_text, "Notes")

            # Payment Type (default is "check", no need to change)

            # Status = Received (value="1")
            status_select = self.adapter.page.locator('select[wire\\:model="form.status"]').first
            status_select.select_option("1")
            self.logger.info(f"    ✓ Status: Received")

            # Date Issued
            date_input = self.adapter.page.locator('input[wire\\:model="form.issue_date"]').first
            self._fill_livewire_field(date_input, check_data.check_date, "Date Issued")

            # Date Received (use today's date)
            today = datetime.now().strftime('%Y-%m-%d')
            received_input = self.adapter.page.locator('input[wire\\:model="form.date_received"]').first
            self._fill_livewire_field(received_input, today, "Date Received")

            # Click Images tab to reveal file upload section
            self.logger.info(f"  Switching to Images tab...")
            images_tab = self.adapter.page.locator('button:has-text("Images")').first
            images_tab.click()
            self.adapter.page.wait_for_timeout(1000)

            # Upload front image (the check PDF)
            self.logger.info(f"  Uploading check PDF...")
            file_input = self.adapter.page.locator('input[wire\\:model="form.front_file"]').first
            file_input.set_input_files(str(check_pdf_path))

            # Wait for Livewire upload to complete
            self.logger.info(f"    Waiting for Livewire file upload to complete...")
            self.adapter.page.wait_for_timeout(2000)

            # Wait for Livewire loading overlay to disappear
            try:
                loading_overlay = self.adapter.page.locator('[wire\\:loading]').first
                loading_overlay.wait_for(state='hidden', timeout=15000)
                self.logger.info(f"    ✓ Livewire upload finished")
            except:
                self.logger.info(f"    ✓ No loading overlay found (upload may be instant)")

            # Extra wait to ensure Livewire state is updated
            self.adapter.page.wait_for_timeout(1000)

            self.logger.info(f"    ✓ Check PDF uploaded")

            # DON'T switch back to Status tab - Apply button is only visible from Images tab
            self.logger.info(f"  Staying on Images tab (Apply button not visible from Status)")
            self.adapter.page.wait_for_timeout(1000)

            self.logger.info(f"  ✓ Form filled successfully")

        except Exception as e:
            raise FormSubmissionError(f"Failed to fill check form: {e}")

    def _submit_form(self):
        """Submit the carrier check form."""
        try:
            self.logger.info(f"  Submitting form...")

            # Wait a moment to ensure all Livewire updates are complete
            self.adapter.page.wait_for_timeout(1000)

            # Find Apply button (NOT "Save" - the button actually says "Apply")
            save_button = self.adapter.page.locator('button[type="submit"]:has-text("Apply")').first

            # Check if button is enabled (not disabled)
            self.logger.info(f"  Checking if Apply button is enabled...")
            is_disabled = save_button.get_attribute('disabled')
            if is_disabled:
                self.logger.warning(f"  Apply button is disabled, waiting for it to become enabled...")
                self.adapter.page.wait_for_timeout(3000)
                is_disabled = save_button.get_attribute('disabled')
                if is_disabled:
                    raise FormSubmissionError("Apply button is still disabled after waiting")

            self.logger.info(f"  Apply button is enabled")

            # Manually populate Livewire's data object from DOM values
            self.logger.info(f"  Manually syncing DOM values to Livewire state...")

            sync_result = self.adapter.page.evaluate('''() => {
                const components = window.Livewire?.all() || [];
                if (components.length === 0) return {success: false, error: 'No components'};

                const comp = components[0];

                // Get values from DOM (need to escape colon in attribute selector)
                const amount = document.querySelector('input[wire\\\\:model="form.amount"]')?.value;
                const refId = document.querySelector('input[wire\\\\:model="form.reference_id"]')?.value;
                const name = document.querySelector('input[wire\\\\:model="form.name"]')?.value;
                const notes = document.querySelector('textarea[wire\\\\:model="form.notes"]')?.value;
                const status = document.querySelector('select[wire\\\\:model="form.status"]')?.value;
                const issueDate = document.querySelector('input[wire\\\\:model="form.issue_date"]')?.value;
                const dateReceived = document.querySelector('input[wire\\\\:model="form.date_received"]')?.value;

                // Manually set Livewire's internal data
                if (!comp.canonical) comp.canonical = {};
                if (!comp.canonical.data) comp.canonical.data = {};
                comp.canonical.data.form = {
                    amount: amount,
                    reference_id: refId,
                    name: name,
                    notes: notes,
                    status: status,
                    issue_date: issueDate,
                    date_received: dateReceived
                };

                return {
                    success: true,
                    values: {amount, refId, name, status}
                };
            }''')

            self.logger.info(f"  Sync result: {sync_result}")

            # Verify Livewire actually has the data now
            verify = self.adapter.page.evaluate('''() => {
                const comp = window.Livewire?.all()[0];
                return {
                    hasForm: comp?.canonical?.data?.form !== null,
                    amount: comp?.canonical?.data?.form?.amount
                };
            }''')
            self.logger.info(f"  Verified Livewire state after sync: {verify}")

            # Now click the Apply button
            self.logger.info(f"  Clicking Apply button after manual sync...")
            try:
                save_button.click(force=True, timeout=5000)
            except Exception as e:
                self.logger.warning(f"  Force click failed: {e}, trying JavaScript...")
                self.adapter.page.evaluate('''() => {
                    const btn = document.querySelector('button[type="submit"]');
                    if (btn && btn.textContent.includes('Apply')) {
                        btn.click();
                    }
                }''')
            self.logger.info(f"  ✓ Clicked Apply button")

            # Wait for the form submission to be processed (AJAX-based)
            self.adapter.page.wait_for_timeout(3000)

            # Debug: Check if any Livewire errors appeared
            try:
                livewire_error = self.adapter.page.locator('[x-show="hasError"]').first
                if livewire_error.is_visible(timeout=1000):
                    error_text = livewire_error.inner_text()
                    self.logger.error(f"  Livewire error visible: {error_text}")
            except:
                pass

            self.logger.info(f"  ✓ Form click completed")

            # Wait for submission to complete and slideover to close
            self.logger.info(f"  Waiting for form submission to complete...")
            self.adapter.page.wait_for_timeout(5000)

            # Verify success - check if slideover closed
            slideover_closed = False
            try:
                slideover_footer = self.adapter.page.locator('div.slideover-footer').first
                if slideover_footer.is_visible(timeout=2000):
                    self.logger.warning("Slideover still visible after 5s - checking for validation errors...")

                    # Check for validation error messages
                    error_messages = self.adapter.page.locator('.text-danger, .text-red-500, .error, [role="alert"]')
                    error_count = error_messages.count()
                    if error_count > 0:
                        self.logger.error(f"Found {error_count} validation error(s):")
                        for i in range(min(error_count, 5)):  # Log first 5 errors
                            try:
                                error_text = error_messages.nth(i).inner_text(timeout=1000)
                                self.logger.error(f"  Error {i+1}: {error_text}")
                            except:
                                pass
                    else:
                        self.logger.info("  No validation errors found in DOM")

                        # Debug: Check if Apply button is actually clickable
                        btn_debug = self.adapter.page.evaluate('''() => {
                            const btn = document.querySelector('button[type="submit"]');
                            return {
                                exists: !!btn,
                                disabled: btn?.disabled,
                                visible: btn?.offsetParent !== null,
                                text: btn?.textContent
                            };
                        }''')
                        self.logger.info(f"  Apply button state: {btn_debug}")

                    # Take screenshot and dump HTML
                    screenshot_dir = self.config.SCREENSHOTS_DIR
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    screenshot_path = screenshot_dir / f"form_not_submitting_{timestamp}.png"
                    self.adapter.page.screenshot(path=str(screenshot_path))
                    self.logger.error(f"Screenshot saved: {screenshot_path}")

                    # Dump slideover HTML for debugging
                    html_path = screenshot_dir / f"form_html_{timestamp}.html"
                    slideover_html = self.adapter.page.evaluate('''() => {
                        const slideover = document.querySelector('.slideover, [class*="slideover"]');
                        return slideover ? slideover.outerHTML : document.body.innerHTML;
                    }''')
                    with open(html_path, 'w') as f:
                        f.write(slideover_html)
                    self.logger.error(f"HTML dumped: {html_path}")

                    # Wait longer and check again
                    self.adapter.page.wait_for_timeout(5000)
                    if slideover_footer.is_visible(timeout=2000):
                        raise FormSubmissionError("Slideover did not close after 10s - form submission failed (check screenshot for validation errors)")
                    else:
                        slideover_closed = True
                        self.logger.info(f"  ✓ Slideover closed after extended wait")
                else:
                    slideover_closed = True
                    self.logger.info(f"  ✓ Slideover closed - submission successful")
            except FormSubmissionError:
                raise
            except:
                # Slideover not visible = success
                slideover_closed = True
                self.logger.info(f"  ✓ Slideover closed - submission successful")

            self.logger.info(f"  ✓ Form submitted")

        except Exception as e:
            raise FormSubmissionError(f"Failed to submit check form: {e}")
