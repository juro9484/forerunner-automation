"""
AI Summarizer module for Forerunner Claims Automation.
Generates concise summaries of claim-related emails using Claude AI.
"""

import logging
from typing import Optional, Any
from datetime import datetime
import anthropic
from dataclasses import dataclass

from config import Config
from email_monitor import EmailData


@dataclass
class EmailSummary:
    """
    Structured container for email summary results.

    Attributes:
        claim_number: The claim number this summary is for
        title: The note title in format "M.D.YY [Person] [action] [to/from] [recipient]"
        description: Concise third-person description of the email content
        timestamp: When the summary was generated
        model_used: Which AI model generated the summary
    """
    claim_number: str
    title: str
    description: str
    timestamp: datetime
    model_used: str


class SummarizerError(Exception):
    """Base exception for summarizer errors."""
    pass


class AIAPIError(SummarizerError):
    """Raised when AI API calls fail."""
    pass


class EmailSummarizer:
    """
    Handles AI-powered summarization of claim emails using Claude.

    This class interfaces with the Anthropic Claude API to generate
    concise, professional summaries of insurance claim emails suitable
    for posting to the Claim Titan CRM.
    """

    # Claude model to use (3.5 Haiku - smart, fast, and cost-effective for summarization)
    MODEL = "claude-3-5-haiku-20241022"

    # System prompt that defines Claude's role and output format
    SYSTEM_PROMPT = """You are an AI assistant for Forerunner Claims, an insurance claims processing company.
Your job is to read emails related to insurance claims and create notes for the Claim Titan CRM system.

Each note consists of two parts:

1. **TITLE** - Format: "[Date] [Person] [action] [to/from] [recipient/company]"
   - Date in M.D.YY format (e.g., "9.8.25", "10.27.25")
   - Person who sent the email (first name or full name from signature/context)
   - Action: "sent email", "replied to email", "followed up", etc.
   - Recipient name and company abbreviation if known (e.g., "Lynn of SF" for State Farm)
   - Examples:
     * "9.8.25 Beau sent email follow up to Lynn of SF"
     * "10.27.25 Dorothy replied to Beau email"

2. **DESCRIPTION** - A concise third-person past-tense summary including:
   - Start with who contacted whom (e.g., "Beau contacted State Farm letting them know...", "Dorothy replied to Beau regarding...")
   - What documents were sent/requested
   - Key dates, amounts, and deadlines mentioned
   - Legal references or policy numbers if cited
   - Specific questions asked or requests made
   - Important context or concerns raised
   - NO generic pleasantries or fluff - only critical facts
   - Use the From/To email fields to identify sender and recipient accurately

Writing style:
- Third person past tense (e.g., "Beau sent", "Dorothy asked")
- Concise but detailed with critical information
- Include specific dollar amounts, dates, names, document types
- Professional insurance industry terminology
- Focus on facts and actions, not opinions

**CRITICAL FORMATTING RULES:**
- Format the ENTIRE description as a SINGLE FLOWING PARAGRAPH
- DO NOT use literal line breaks, newlines, or bullet points within the description
- Use inline numbered items like "1) first item, 2) second item, 3) third item" or semicolons to separate multiple points
- Keep all text in one continuous paragraph for proper JSON formatting

Format your response as JSON:
{
    "title": "Date [Person] [action] [to/from] [recipient]",
    "description": "Concise third-person description with critical details..."
}"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the email summarizer.

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

        self.logger.info(f"EmailSummarizer initialized with model: {self.MODEL}")

    def summarize_email(
        self,
        email_data: EmailData,
        max_retries: int = 3
    ) -> EmailSummary:
        """
        Generate an AI summary of an email using Claude.

        Args:
            email_data: EmailData object containing the email to summarize
            max_retries: Maximum number of retry attempts on failure

        Returns:
            EmailSummary object containing the generated summary

        Raises:
            AIAPIError: If AI API call fails after all retries
            SummarizerError: If summary generation fails for other reasons
        """
        self.logger.info(
            f"Generating summary for claim {email_data.claim_number} "
            f"(email from {email_data.sender})"
        )

        # Build the user prompt with email details
        user_prompt = self._build_prompt(email_data)

        # Try to get summary with retries
        for attempt in range(max_retries):
            try:
                # Call Claude API
                response = self.client.messages.create(
                    model=self.MODEL,
                    max_tokens=1024,
                    system=self.SYSTEM_PROMPT,
                    messages=[
                        {
                            "role": "user",
                            "content": user_prompt
                        }
                    ]
                )

                # Parse the response
                summary_data = self._parse_response(response)

                # Create EmailSummary object
                email_summary = EmailSummary(
                    claim_number=email_data.claim_number,
                    title=summary_data["title"],
                    description=summary_data["description"],
                    timestamp=datetime.now(),
                    model_used=self.MODEL
                )

                self.logger.info(
                    f"Successfully generated summary for claim {email_data.claim_number}"
                )

                return email_summary

            except anthropic.APIError as e:
                self.logger.error(
                    f"Anthropic API error (attempt {attempt + 1}/{max_retries}): {e}"
                )
                if attempt == max_retries - 1:
                    raise AIAPIError(f"AI API failed after {max_retries} attempts: {e}")

            except Exception as e:
                self.logger.error(
                    f"Unexpected error during summarization (attempt {attempt + 1}/{max_retries}): {e}"
                )
                if attempt == max_retries - 1:
                    raise SummarizerError(f"Summarization failed: {e}")

    def _strip_quoted_replies(self, email_body: str) -> str:
        """
        Strip quoted/forwarded content from email body to get only the new message.

        The NEWEST message is at the TOP of the email. This function removes everything
        below the first quoted/forwarded message to preserve only the latest reply.

        Args:
            email_body: Full email body including quoted replies

        Returns:
            Email body with quoted content removed (newest message only)
        """
        import re

        lines = email_body.split('\n')
        new_lines = []

        for i, line in enumerate(lines):
            line_stripped = line.strip()

            # STRICT email header detection in body (indicates quoted message)
            # Must have actual email format: From: Name <email@domain.com> or From: email@domain.com
            # Skip first 3 lines to avoid matching real email headers
            if i >= 3:
                # From: with email address pattern (very strict)
                if re.match(r'^\s*From:\s+.*[<]?[\w\.-]+@[\w\.-]+[>]?', line, re.IGNORECASE):
                    # This is a quoted message header - stop here
                    break

                # To: with email address pattern (very strict)
                if re.match(r'^\s*To:\s+.*[<]?[\w\.-]+@[\w\.-]+[>]?', line, re.IGNORECASE):
                    # Also indicates quoted message - stop here
                    break

                # Date: followed by typical date format (in body, not at top)
                if re.match(r'^\s*Date:\s+\w+,?\s+\w+\s+\d+', line, re.IGNORECASE):
                    # Date header in body indicates quoted message
                    break

                # Sent: followed by date (Outlook style)
                if re.match(r'^\s*Sent:\s+\w+,?\s+\w+\s+\d+', line, re.IGNORECASE):
                    # Outlook "Sent:" header
                    break

            # Other common quote patterns
            if (
                line_stripped.startswith('>') or  # > quoted text (very common)
                (line_stripped.startswith('On ') and ' wrote:' in line) or  # On [date] [person] wrote:
                '-----Original Message-----' in line or  # Outlook forward
                '________________________________' in line or  # Outlook separator (long line of underscores)
                re.match(r'^[-_]{8,}$', line_stripped) or  # Line of 8+ dashes/underscores (separator)
                'begin forwarded message' in line_stripped.lower() or  # Apple Mail forward
                line.strip() == '---' and i > 5  # Common separator (after some content)
            ):
                # Stop processing at first quote marker
                break

            new_lines.append(line)

        # Join lines and clean up excessive whitespace
        result = '\n'.join(new_lines).strip()

        # Remove trailing signatures if they appear
        # Common signature patterns
        signature_patterns = [
            r'\n\s*--\s*\n',  # -- signature separator
            r'\n\s*Sent from my ',  # Mobile signatures
            r'\n\s*Get Outlook for ',  # Outlook mobile
        ]

        for pattern in signature_patterns:
            parts = re.split(pattern, result, maxsplit=1)
            if len(parts) > 1:
                result = parts[0].strip()
                break

        return result

    def _build_prompt(self, email_data: EmailData) -> str:
        """
        Build the user prompt from email data.

        Args:
            email_data: EmailData object to build prompt from

        Returns:
            Formatted prompt string
        """
        # Strip quoted replies to get only the new message
        clean_content = self._strip_quoted_replies(email_data.email_content)

        prompt = f"""Please summarize this insurance claim email:

**Claim Number:** {email_data.claim_number}
**From:** {email_data.sender}
**To:** {email_data.recipient}
**Subject:** {email_data.subject}
**Date:** {email_data.timestamp.strftime('%Y-%m-%d %H:%M:%S')}

**Email Content:**
{clean_content}

---

**IMPORTANT:** This email content has been cleaned to show only the newest message from the sender.
Use the From/To fields to accurately identify who sent this message and who received it.
Create a title and description that reflects the sender's communication in THIS specific message.

Please provide a summary in the JSON format specified."""

        return prompt

    def _parse_response(self, response: Any) -> dict:
        """
        Parse Claude's response and extract summary data.

        Args:
            response: Response from Claude API

        Returns:
            Dictionary with summary, key_points, and action_items

        Raises:
            SummarizerError: If response cannot be parsed
        """
        import json

        try:
            # Get the text content from response
            content = response.content[0].text

            # Try to extract JSON from the response
            # Claude sometimes wraps JSON in markdown code blocks
            if "```json" in content:
                # Extract JSON from code block
                json_start = content.find("```json") + 7
                json_end = content.find("```", json_start)
                json_str = content[json_start:json_end].strip()
            elif "```" in content:
                # Try generic code block
                json_start = content.find("```") + 3
                json_end = content.find("```", json_start)
                json_str = content[json_start:json_end].strip()
            else:
                # Assume the entire content is JSON
                json_str = content.strip()

            # Parse the JSON
            try:
                summary_data = json.loads(json_str)
            except json.JSONDecodeError as e:
                # Try cleaning control characters and parsing again
                self.logger.warning(f"Initial JSON parse failed, attempting to clean control characters...")
                import re
                # Remove control characters except newline, tab, carriage return
                json_str_cleaned = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', json_str)
                summary_data = json.loads(json_str_cleaned)

            # Validate required fields
            required_fields = ["title", "description"]
            for field in required_fields:
                if field not in summary_data:
                    raise ValueError(f"Missing required field: {field}")

            return summary_data

        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON response: {e}")
            self.logger.error(f"Raw response content (first 500 chars): {content[:500]}")
            self.logger.error(f"Extracted JSON string (first 500 chars): {json_str[:500]}")
            raise SummarizerError(f"Could not parse AI response as JSON: {e}")

        except Exception as e:
            self.logger.error(f"Error parsing response: {e}")
            raise SummarizerError(f"Failed to parse response: {e}")

    def format_for_crm(self, email_summary: EmailSummary) -> str:
        """
        Format the summary for posting to Claim Titan CRM.

        Args:
            email_summary: EmailSummary object to format

        Returns:
            Formatted string ready for CRM posting
        """
        lines = []

        # Title
        lines.append(f"Title: {email_summary.title}")
        lines.append("")

        # Description
        lines.append(f"Description: {email_summary.description}")

        return "\n".join(lines)


def main():
    """
    Example usage of the EmailSummarizer.
    This is for testing purposes only.
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Create a test email similar to real examples
    test_email = EmailData(
        claim_number="12-345",
        email_content="""
        Hi Lynn,

        Following up on the estimate and documentation we submitted on August 27th for Devin's claim.

        Has the file been reassigned as we discussed? Per CA Regulation 2695.5(b), we need a
        response within 15 days of submission.

        Also still need:
        - Name of contractor who inspected on July 23rd
        - Their estimate and report
        - Photos from that inspection

        We need to review scope differences and may need to schedule a reinspection.

        Thanks,
        Beau
        Forerunner Claims
        """,
        sender="beau@forerunnerclaims.com",
        recipient="lynn@statefarm.com",
        subject="Re: Claim 12-345 - Follow up on submitted documentation",
        timestamp=datetime(2025, 9, 8, 14, 30),
        email_id="test123"
    )

    try:
        # Initialize summarizer
        summarizer = EmailSummarizer()

        # Generate summary
        summary = summarizer.summarize_email(test_email)

        # Print formatted output
        print("\n" + "="*60)
        print("CRM NOTE FORMAT:")
        print("="*60)
        print(summarizer.format_for_crm(summary))
        print("="*60)
        print(f"\nClaim Number: {summary.claim_number}")
        print(f"Generated: {summary.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Model: {summary.model_used}")
        print("="*60 + "\n")

    except Exception as e:
        logging.error(f"Test failed: {e}")
        raise


if __name__ == "__main__":
    main()
