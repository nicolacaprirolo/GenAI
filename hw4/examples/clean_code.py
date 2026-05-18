"""Sample clean code with no PII - used to test false positive rate."""

from datetime import datetime


def calculate_total(items: list[dict]) -> float:
    """Calculate total cost of items."""
    return sum(item["price"] * item["quantity"] for item in items)


def format_currency(amount: float) -> str:
    """Format amount as USD."""
    return f"${amount:,.2f}"


def is_business_hours(now: datetime) -> bool:
    """Check if current time is during business hours (9am-5pm)."""
    return 9 <= now.hour < 17


def get_product_categories() -> list[str]:
    """Return available product categories."""
    return ["electronics", "books", "clothing", "home", "garden"]


PRICING_TIERS = {
    "basic": 9.99,
    "pro": 29.99,
    "enterprise": 99.99,
}

VERSION = "2.1.0"
MAX_RETRY_COUNT = 3
DEFAULT_TIMEOUT_SECONDS = 30
