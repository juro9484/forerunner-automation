"""
Contract Parser module for Forerunner Claims Automation.
Extracts client and claim data from insurance contract PDFs using Claude AI.
"""

import logging
import base64
import json
from typing import Optional
from datetime import datetime
from dataclasses import dataclass
import anthropic

from config import Config


@dataclass
class ClientData:
    """
    Structured container for client data extracted from contract.

    Attributes:
        first_name: Client's first name (REQUIRED for Claim Titan)
        last_name: Client's last name (optional but recommended)
        email: Client's email address
        phone: Client's phone number
        street_address: Property street address (REQUIRED)
        city: Property city (REQUIRED)
        state: Property state 2-letter code (REQUIRED)
        zipcode: Property zipcode (REQUIRED)
        insurance_company: Insurance company name
        policy_number: Insurance policy number
        claim_number: Insurance claim number
        loss_type: Type of loss (fire, water, wind, etc.)
        loss_date: Date of loss
        contract_date: Date contract was signed
    """
    # Required fields
    first_name: str
    street_address: str
    city: str
    state: str
    zipcode: str

    # Optional fields
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    insurance_company: Optional[str] = None
    policy_number: Optional[str] = None
    claim_number: Optional[str] = None
    loss_type: Optional[str] = None
    loss_date: Optional[str] = None
    contract_date: Optional[str] = None


class ContractParserError(Exception):
    """Base exception for contract parser errors."""
    pass


class ContractParser:
    """
    Handles AI-powered extraction of client data from insurance contract PDFs.

    Uses Claude's vision API to read PDF contracts and extract structured data
    for creating new claims in Claim Titan CRM.
    """

    # Claude model to use - configurable via CLAUDE_VISION_MODEL env var
    # Defaults to Opus which has superior vision capabilities for PDFs
    MODEL = Config.CLAUDE_VISION_MODEL

    # System prompt for contract parsing
    EXTRACTION_PROMPT = """You are extracting client and claim information from an insurance public adjuster contract.

Extract the following information from the contract and return it as JSON:

**REQUIRED FIELDS (must be present):**
- first_name: Client's first name from "Name of Insured" field
- last_name: Client's last name (if available, otherwise null)
- street_address: Full street address from "property located at" field
- city: City name from address
- state: 2-letter state code (e.g., CA, CO, NY)
- zipcode: ZIP code from address

**OPTIONAL FIELDS (extract if available):**
- email: Client's email address (check audit trail/signatures)
- phone: Client's phone number
- insurance_company: Insurance company name ("The Insurer is...")
- policy_number: Policy number
- claim_number: Claim number
- loss_type: Cause of loss (fire, water, wind, hail, etc.)
- loss_date: Date of loss in YYYY-MM-DD format
- contract_date: Effective date of contract in YYYY-MM-DD format

**IMPORTANT FORMATTING RULES:**
1. Return ONLY valid JSON, no additional text or explanation
2. Use null for any field that cannot be found
3. For loss_type, read EXACTLY what is written in the "Cause of loss" blank and use lowercase
4. For dates, use YYYY-MM-DD format (e.g., "2026-01-28")
5. Extract state as 2-letter code only (CO, not Colorado)
6. Clean up addresses - remove extra spaces, format nicely

CRITICAL: Read the "Cause of loss" field VERY CAREFULLY character by character. Do not guess or assume.

Now extract the data from the provided contract and return ONLY the JSON."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the contract parser.

        Args:
            api_key: Anthropic API key. If not provided, uses Config.ANTHROPIC_API_KEY

        Raises:
            ValueError: If no API key is available
        """
        self.api_key = api_key or Config.ANTHROPIC_API_KEY

        if not self.api_key:
            raise ValueError(
                "Anthropic API key not found. Set ANTHROPIC_API_KEY in .env file"
            )

        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.logger = logging.getLogger(__name__)

        self.logger.info("ContractParser initialized")

    def parse_contract(self, pdf_path: str) -> ClientData:
        """
        Extract client data from a contract PDF.

        Args:
            pdf_path: Path to the contract PDF file

        Returns:
            ClientData object with extracted information

        Raises:
            ContractParserError: If parsing fails or required fields are missing
        """
        self.logger.info(f"Parsing contract: {pdf_path}")

        try:
            # Read and encode PDF
            with open(pdf_path, 'rb') as f:
                pdf_data = f.read()

            pdf_base64 = base64.standard_b64encode(pdf_data).decode('utf-8')

            # Call Claude API with vision
            self.logger.info("Sending PDF to Claude for extraction...")
            response = self.client.messages.create(
                model=self.MODEL,
                max_tokens=2048,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "document",
                                "source": {
                                    "type": "base64",
                                    "media_type": "application/pdf",
                                    "data": pdf_base64
                                }
                            },
                            {
                                "type": "text",
                                "text": self.EXTRACTION_PROMPT
                            }
                        ]
                    }
                ]
            )

            # Parse response
            extracted_data = self._parse_response(response)

            # Create ClientData object
            client_data = ClientData(
                first_name=extracted_data["first_name"],
                last_name=extracted_data.get("last_name"),
                email=extracted_data.get("email"),
                phone=extracted_data.get("phone"),
                street_address=extracted_data["street_address"],
                city=extracted_data["city"],
                state=extracted_data["state"],
                zipcode=extracted_data["zipcode"],
                insurance_company=extracted_data.get("insurance_company"),
                policy_number=extracted_data.get("policy_number"),
                claim_number=extracted_data.get("claim_number"),
                loss_type=extracted_data.get("loss_type"),
                loss_date=extracted_data.get("loss_date"),
                contract_date=extracted_data.get("contract_date")
            )

            self.logger.info(
                f"✓ Successfully extracted client data: {client_data.first_name} "
                f"{client_data.last_name or ''} - {client_data.street_address}"
            )

            return client_data

        except Exception as e:
            self.logger.error(f"Failed to parse contract: {e}", exc_info=True)
            raise ContractParserError(f"Contract parsing failed: {e}")

    def _parse_response(self, response) -> dict:
        """
        Parse Claude's response and extract JSON data.

        Args:
            response: Response from Claude API

        Returns:
            Dictionary with extracted client data

        Raises:
            ContractParserError: If response cannot be parsed or required fields missing
        """
        try:
            # Get the text content from response
            content = response.content[0].text

            # Try to extract JSON from the response
            # Claude sometimes wraps JSON in markdown code blocks
            if "```json" in content:
                json_start = content.find("```json") + 7
                json_end = content.find("```", json_start)
                json_str = content[json_start:json_end].strip()
            elif "```" in content:
                json_start = content.find("```") + 3
                json_end = content.find("```", json_start)
                json_str = content[json_start:json_end].strip()
            else:
                json_str = content.strip()

            # Parse JSON
            data = json.loads(json_str)

            # Validate required fields
            required_fields = ["first_name", "street_address", "city", "state", "zipcode"]
            missing_fields = [field for field in required_fields if not data.get(field)]

            if missing_fields:
                raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")

            self.logger.info("✓ Successfully parsed contract data")
            return data

        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON response: {e}")
            self.logger.error(f"Raw response: {content[:500]}")
            raise ContractParserError(f"Could not parse AI response as JSON: {e}")

        except Exception as e:
            self.logger.error(f"Error parsing response: {e}")
            raise ContractParserError(f"Failed to parse response: {e}")


def main():
    """
    Example usage of the ContractParser.
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    import sys

    if len(sys.argv) < 2:
        print("Usage: python contract_parser.py <path_to_contract.pdf>")
        sys.exit(1)

    contract_path = sys.argv[1]

    try:
        # Initialize parser
        parser = ContractParser()

        # Parse contract
        client_data = parser.parse_contract(contract_path)

        # Print results
        print("\n" + "="*80)
        print("EXTRACTED CLIENT DATA")
        print("="*80)
        print(f"Name: {client_data.first_name} {client_data.last_name or ''}")
        print(f"Email: {client_data.email or '(not found)'}")
        print(f"Phone: {client_data.phone or '(not found)'}")
        print(f"\nProperty Address:")
        print(f"  {client_data.street_address}")
        print(f"  {client_data.city}, {client_data.state} {client_data.zipcode}")
        print(f"\nInsurance Info:")
        print(f"  Company: {client_data.insurance_company or '(not found)'}")
        print(f"  Policy #: {client_data.policy_number or '(not found)'}")
        print(f"  Claim #: {client_data.claim_number or '(not found)'}")
        print(f"\nLoss Info:")
        print(f"  Type: {client_data.loss_type or '(not found)'}")
        print(f"  Date: {client_data.loss_date or '(not found)'}")
        print(f"\nContract Date: {client_data.contract_date or '(not found)'}")
        print("="*80 + "\n")

    except Exception as e:
        logging.error(f"Failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
