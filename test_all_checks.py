#!/usr/bin/env python3
"""Test check parser on all sample PDFs."""

import sys
from pathlib import Path

sys.path.insert(0, 'src')

from check_parser import CheckParser
import logging

logging.basicConfig(level=logging.WARNING)

check_files = [
    "Yospe_Dwelling Check 7.18.25.pdf",
    "Green_Liberty Mutual Check 8.13.25.pdf",
    "McFarland_Chubb Check 5.22.25.pdf",
    "Bentley_State Farm Check 10.11.25.pdf",
    "DeHaan_Dwelling Check.pdf",
    "Goldberger_USAA Dwelling Check 1.15.25 VOID.pdf",
    "Hascall_Dwelling Payment 11.26.25.pdf"
]

parser = CheckParser()

print("\n" + "="*100)
print("TESTING CHECK PARSER ON 7 SAMPLE CHECKS")
print("="*100 + "\n")

for i, filename in enumerate(check_files, 1):
    pdf_path = Path.home() / "Downloads" / filename

    if not pdf_path.exists():
        print(f"{i}. ✗ NOT FOUND: {filename}\n")
        continue

    print(f"{i}. {filename}")
    print("-" * 100)

    check_data = parser.parse_check(pdf_path)

    if check_data:
        print(f"   ✓ SUCCESS ({check_data.overall_confidence}% confidence)")
        print(f"   Claim #:        {check_data.claim_number}")
        print(f"   Amount:         ${check_data.check_amount}")
        print(f"   Check #:        {check_data.check_number}")
        print(f"   Date:           {check_data.check_date}")
        print(f"   Payer:          {check_data.payer}")
        print(f"   Insured:        {check_data.insured_name}")
        print(f"   Field Scores:   Amount={check_data.amount_confidence}%, Check#={check_data.check_number_confidence}%, Date={check_data.date_confidence}%")
        print(f"                   Claim#={check_data.claim_number_confidence}%, Payer={check_data.payer_confidence}%, Insured={check_data.insured_confidence}%")

        if check_data.overall_confidence >= 95:
            print(f"   Status:         🟢 HIGH CONFIDENCE - Auto-process")
        elif check_data.overall_confidence >= 80:
            print(f"   Status:         🟡 MEDIUM CONFIDENCE - Review recommended")
        else:
            print(f"   Status:         🔴 LOW CONFIDENCE - Manual entry required")
    else:
        print(f"   ✗ FAILED to extract data")

    print()

print("="*100)
print("TEST COMPLETE")
print("="*100)
