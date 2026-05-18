"""Negative test case: things that look like PII but aren't.

This file contains strings that pattern-match common PII regexes
but are not actually PII. The detector should NOT flag these.
"""

# Version strings that look like phone numbers
VERSION = "1.2.3"
RELEASE_DATE = "2024-05-18"
BUILD_NUMBER = "20240518.1"

# IDs that look like SSNs
USER_ID_FORMAT = "000-00-0000"  # template, not real SSN
TICKET_NUMBER = "INC-2024-001234"

# Numbers that look like credit cards
SAMPLE_TRANSACTION_ID = "1234567890123456"  # Not Luhn valid
ORDER_ID = "ORD-9999-1234-5678-9012"

# Generic placeholders
PLACEHOLDER_PHONE = "(000) 000-0000"
PLACEHOLDER_CPF = "000.000.000-00"

# Configuration values
TIMEOUT_SECONDS = 30
MAX_RETRIES = 3
PORT_NUMBER = 8080
PAGE_SIZE = 100

# Mathematical operations
def calculate_age(birth_year: int) -> int:
    """Calculate age, not store DOB."""
    current_year = 2026
    return current_year - birth_year

# Function names that contain "email" or "phone" but aren't PII
def validate_email_format(email_string: str) -> bool:
    """Generic email validation."""
    return "@" in email_string

def format_phone_number(digits: str) -> str:
    """Generic phone formatter."""
    return digits
