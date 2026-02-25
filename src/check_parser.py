"""
Check Parser - Extracts data from insurance check PDF scans.
Uses Claude Vision (Opus 4.5) for robust OCR and data extraction.
Handles multiple insurance company formats with confidence scoring.
"""

import logging
import base64
import json
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass

import anthropic

from config import Config


@dataclass
class CheckData:
    """Structured check data extracted from PDF scan."""
    check_amount: str
    check_number: str
    check_date: str
    payer: str
    insured_name: str
    claim_number: str

    # Confidence scores (0-100)
    amount_confidence: int
    check_number_confidence: int
    date_confidence: int
    payer_confidence: int
    insured_confidence: int
    claim_number_confidence: int

    # Overall confidence
    overall_confidence: int

    # Extraction notes
    notes: str

    # Raw extraction for audit
    raw_first_pass: Dict[str, Any]
    raw_second_pass: Dict[str, Any]


class CheckParser:
    """
    Parses insurance check PDFs using Claude Vision.
    Handles multiple insurance company formats with two-pass verification.
    One PDF = One check (even if multi-page). Claude Vision reads all pages.
    """

    def __init__(self):
        """Initialize check parser with Claude client."""
        self.logger = logging.getLogger(__name__)
        self.client = anthropic.Anthropic(api_key=Config.ANTHROPIC_API_KEY)
        self.vision_model = Config.CLAUDE_VISION_MODEL

    def parse_check(self, pdf_path) -> Optional[CheckData]:
        """
        Parse a check PDF and extract structured data.
        Handles multi-page PDFs (blank pages, summary + check image, etc).

        Args:
            pdf_path: Path to check PDF file (string or Path object)

        Returns:
            CheckData if extraction successful, None otherwise
        """
        try:
            # Convert to Path if string
            if isinstance(pdf_path, str):
                pdf_path = Path(pdf_path)

            self.logger.info(f"Parsing check PDF: {pdf_path.name}")

            # Read and encode entire PDF (Claude Vision will read all pages)
            pdf_data = self._read_pdf(pdf_path)
            if not pdf_data:
                return None

            # First pass: Extract data
            first_pass = self._extract_check_data(pdf_data)
            if not first_pass:
                self.logger.error("First pass extraction failed")
                return None

            self.logger.info("First pass extraction complete")
            self.logger.info(f"  Claim #: {first_pass.get('claim_number', 'N/A')}")
            self.logger.info(f"  Amount: ${first_pass.get('check_amount', 'N/A')}")
            self.logger.info(f"  Overall confidence: {first_pass.get('overall_confidence', 0)}%")

            # Second pass: Verify extraction
            second_pass = self._verify_check_data(pdf_data, first_pass)
            if not second_pass:
                self.logger.warning("Second pass verification failed, using first pass only")
                second_pass = first_pass
            else:
                self.logger.info("Second pass verification complete")
                self.logger.info(f"  Verification confidence: {second_pass.get('overall_confidence', 0)}%")

            # Build CheckData with both passes
            check_data = self._build_check_data(first_pass, second_pass)

            # Log final confidence
            if check_data.overall_confidence >= 95:
                self.logger.info(f"✓ High confidence extraction ({check_data.overall_confidence}%) - Safe to auto-process")
            elif check_data.overall_confidence >= 80:
                self.logger.warning(f"⚠ Medium confidence extraction ({check_data.overall_confidence}%) - Manual review recommended")
            else:
                self.logger.error(f"✗ Low confidence extraction ({check_data.overall_confidence}%) - Skip auto-processing")

            return check_data

        except Exception as e:
            self.logger.error(f"Failed to parse check: {e}", exc_info=True)
            return None

    def _read_pdf(self, pdf_path: Path) -> Optional[str]:
        """Read PDF file and encode as base64."""
        try:
            with open(pdf_path, 'rb') as f:
                pdf_bytes = f.read()
            return base64.standard_b64encode(pdf_bytes).decode('utf-8')
        except Exception as e:
            self.logger.error(f"Failed to read PDF: {e}")
            return None

    def _extract_check_data(self, pdf_data: str) -> Optional[Dict[str, Any]]:
        """First pass: Extract check data from PDF using Claude Vision."""
        try:
            prompt = """You are analyzing an insurance check PDF scan. This PDF may have multiple pages - some with check details/summary, some with the actual check image, and some that are blank. Look across ALL pages to extract the following information:

REQUIRED FIELDS:
1. **check_amount**: The dollar amount of the check (numeric only, e.g., "1307524.01")
2. **check_number**: The check number
3. **check_date**: The date on the check (format: YYYY-MM-DD)
4. **payer**: The insurance company name
5. **insured_name**: The insured person's name (often in "Pay to the order of" line, or listed as "Insured", "Policyholder", or "Claimant")
6. **claim_number**: The claim number (may be labeled as "Claim No", "Claim #", "Loss RPT #", "Claim Ref #", etc.)

For EACH field, provide:
- The extracted value
- A confidence score (0-100) indicating how certain you are
- Any notes about uncertainty or ambiguity

IMPORTANT NOTES:
- The PDF may have multiple pages - look at ALL of them
- Some pages may be blank or contain watermarks - ignore those
- Check details might be on page 1, actual check on page 2 (or vice versa)
- Check layouts vary significantly by insurance company
- Claim numbers can have many formats (D2503529, 059819533-0001, 75-79CO-58W, H9658, etc.)
- Insured name is often in the "Pay to the order of" line (may include mortgage company too)
- Dates can be in various formats (MM/DD/YYYY, MM-DD-YYYY, etc.) - convert to YYYY-MM-DD
- Check amount should be numeric only (remove $ and commas)

Return ONLY valid JSON with this structure:
{
    "check_amount": "value",
    "check_amount_confidence": 95,
    "check_number": "value",
    "check_number_confidence": 95,
    "check_date": "YYYY-MM-DD",
    "check_date_confidence": 95,
    "payer": "Insurance Company Name",
    "payer_confidence": 95,
    "insured_name": "Name",
    "insured_confidence": 95,
    "claim_number": "value",
    "claim_number_confidence": 95,
    "overall_confidence": 95,
    "notes": "Any extraction uncertainties or issues"
}"""

            message = self.client.messages.create(
                model=self.vision_model,
                max_tokens=2000,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "document",
                            "source": {
                                "type": "base64",
                                "media_type": "application/pdf",
                                "data": pdf_data
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }]
            )

            # Parse response
            response_text = message.content[0].text.strip()

            # Extract JSON (may be wrapped in markdown code blocks)
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            return json.loads(response_text)

        except Exception as e:
            self.logger.error(f"First pass extraction failed: {e}", exc_info=True)
            return None

    def _verify_check_data(self, pdf_data: str, first_pass: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Second pass: Verify the extracted data."""
        try:
            prompt = f"""You are VERIFYING a previous extraction of check data. Review the check PDF (all pages) and confirm if these values are correct:

PREVIOUS EXTRACTION:
- Check Amount: ${first_pass.get('check_amount', 'N/A')}
- Check Number: {first_pass.get('check_number', 'N/A')}
- Check Date: {first_pass.get('check_date', 'N/A')}
- Payer: {first_pass.get('payer', 'N/A')}
- Insured Name: {first_pass.get('insured_name', 'N/A')}
- Claim Number: {first_pass.get('claim_number', 'N/A')}

TASK:
Re-examine the check PDF (all pages) and verify each field. If you find any discrepancies or errors, provide the CORRECTED value.

Return ONLY valid JSON with this structure:
{{
    "check_amount": "value (corrected if needed)",
    "check_amount_confidence": 95,
    "check_amount_verified": true/false,
    "check_number": "value (corrected if needed)",
    "check_number_confidence": 95,
    "check_number_verified": true/false,
    "check_date": "YYYY-MM-DD (corrected if needed)",
    "check_date_confidence": 95,
    "check_date_verified": true/false,
    "payer": "value (corrected if needed)",
    "payer_confidence": 95,
    "payer_verified": true/false,
    "insured_name": "value (corrected if needed)",
    "insured_confidence": 95,
    "insured_verified": true/false,
    "claim_number": "value (corrected if needed)",
    "claim_number_confidence": 95,
    "claim_number_verified": true/false,
    "overall_confidence": 95,
    "notes": "Any corrections or issues found during verification"
}}"""

            message = self.client.messages.create(
                model=self.vision_model,
                max_tokens=2000,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "document",
                            "source": {
                                "type": "base64",
                                "media_type": "application/pdf",
                                "data": pdf_data
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }]
            )

            # Parse response
            response_text = message.content[0].text.strip()

            # Extract JSON
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            return json.loads(response_text)

        except Exception as e:
            self.logger.error(f"Second pass verification failed: {e}", exc_info=True)
            return None

    def _build_check_data(self, first_pass: Dict[str, Any], second_pass: Dict[str, Any]) -> CheckData:
        """Build final CheckData from both passes."""

        # Use second pass values (they're verified/corrected)
        # Fall back to first pass if second pass is missing data

        def get_value(key):
            """Get value, preferring second pass."""
            value = second_pass.get(key) or first_pass.get(key) or ""
            # Clean up check_amount - remove $ and commas
            if key == 'check_amount' and value:
                value = value.replace('$', '').replace(',', '').strip()
            return value

        def get_confidence(key):
            """Get confidence, averaging both passes if both exist."""
            first = first_pass.get(f"{key}_confidence", 0)
            second = second_pass.get(f"{key}_confidence", 0)
            if first and second:
                return (first + second) // 2
            return first or second or 0

        # Calculate overall confidence (average of all fields)
        confidences = [
            get_confidence("check_amount"),
            get_confidence("check_number"),
            get_confidence("check_date"),
            get_confidence("payer"),
            get_confidence("insured"),
            get_confidence("claim_number")
        ]
        overall_confidence = sum(confidences) // len(confidences) if confidences else 0

        # Combine notes
        notes_parts = []
        if first_pass.get('notes'):
            notes_parts.append(f"First pass: {first_pass['notes']}")
        if second_pass.get('notes'):
            notes_parts.append(f"Verification: {second_pass['notes']}")
        notes = " | ".join(notes_parts) if notes_parts else "No issues"

        return CheckData(
            check_amount=get_value('check_amount'),
            check_number=get_value('check_number'),
            check_date=get_value('check_date'),
            payer=get_value('payer'),
            insured_name=get_value('insured_name'),
            claim_number=get_value('claim_number'),
            amount_confidence=get_confidence('check_amount'),
            check_number_confidence=get_confidence('check_number'),
            date_confidence=get_confidence('check_date'),
            payer_confidence=get_confidence('payer'),
            insured_confidence=get_confidence('insured'),
            claim_number_confidence=get_confidence('claim_number'),
            overall_confidence=overall_confidence,
            notes=notes,
            raw_first_pass=first_pass,
            raw_second_pass=second_pass
        )


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    parser = CheckParser()

    # Test with a sample check
    test_pdf = Path("~/Downloads/Yospe_Dwelling Check 7.18.25.pdf").expanduser()
    if test_pdf.exists():
        check_data = parser.parse_check(test_pdf)
        if check_data:
            print(f"\n✓ Successfully parsed check:")
            print(f"  Claim #: {check_data.claim_number}")
            print(f"  Amount: ${check_data.check_amount}")
            print(f"  Check #: {check_data.check_number}")
            print(f"  Date: {check_data.check_date}")
            print(f"  Payer: {check_data.payer}")
            print(f"  Insured: {check_data.insured_name}")
            print(f"  Confidence: {check_data.overall_confidence}%")
            print(f"  Notes: {check_data.notes}")
