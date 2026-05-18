#!/usr/bin/env python3
"""PII Detector - scan files for personally identifiable information patterns.

Designed for Brazilian (LGPD) and US (HIPAA) compliance contexts.
Used as a Claude Code skill to scan code, logs, or text before sharing.
"""

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class Finding:
    """A single PII detection match."""

    line: int
    pattern: str
    match: str
    context: str


PATTERNS = {
    "CPF": {
        "regex": r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b",
        "description": "Brazilian taxpayer ID (CPF)",
    },
    "CPF_RAW": {
        "regex": r"\b(?<!\d)\d{11}(?!\d)\b",
        "description": "Brazilian CPF without formatting (11 digits)",
    },
    "CNS": {
        "regex": r"\b\d{3}\s?\d{4}\s?\d{4}\s?\d{4}\b",
        "description": "Brazilian National Health Card (CNS)",
    },
    "SSN": {
        "regex": r"\b\d{3}-\d{2}-\d{4}\b",
        "description": "US Social Security Number",
    },
    "PHONE_BR": {
        "regex": r"\(\d{2}\)\s?\d{4,5}-\d{4}",
        "description": "Brazilian phone number",
    },
    "PHONE_US": {
        "regex": r"\(\d{3}\)\s?\d{3}-\d{4}",
        "description": "US phone number",
    },
    "EMAIL": {
        "regex": r"\b[\w._%+-]+@[\w.-]+\.[A-Za-z]{2,}\b",
        "description": "Email address",
    },
    "DATE_OF_BIRTH": {
        "regex": r"\b(?:0?[1-9]|[12]\d|3[01])[/-](?:0?[1-9]|1[0-2])[/-](?:19|20)\d{2}\b",
        "description": "Date in DD/MM/YYYY or DD-MM-YYYY format",
    },
    "CREDIT_CARD": {
        "regex": r"\b(?:\d[ -]*?){13,16}\b",
        "description": "Credit card number (loose pattern, requires Luhn check)",
    },
    "API_KEY": {
        "regex": r"\b(?:sk-|pk_|api[_-]?key[\"'\s:=]+)[A-Za-z0-9_-]{20,}",
        "description": "API key pattern (Stripe, OpenAI, Anthropic, generic)",
    },
}


def luhn_check(card_number: str) -> bool:
    """Validate credit card with Luhn algorithm."""
    digits = [int(d) for d in re.sub(r"[\s-]", "", card_number) if d.isdigit()]
    if len(digits) < 13 or len(digits) > 19:
        return False
    checksum = 0
    for i, digit in enumerate(reversed(digits)):
        if i % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        checksum += digit
    return checksum % 10 == 0


def is_valid_cpf(cpf: str) -> bool:
    """Validate Brazilian CPF check digits."""
    digits = re.sub(r"\D", "", cpf)
    if len(digits) != 11 or len(set(digits)) == 1:
        return False

    def check_digit(nums: list[int], multipliers: list[int]) -> int:
        total = sum(n * m for n, m in zip(nums, multipliers))
        remainder = total % 11
        return 0 if remainder < 2 else 11 - remainder

    nums = [int(d) for d in digits]
    d1 = check_digit(nums[:9], list(range(10, 1, -1)))
    d2 = check_digit(nums[:10], list(range(11, 1, -1)))
    return nums[9] == d1 and nums[10] == d2


def scan_text(text: str, patterns_filter: list[str] | None = None) -> list[Finding]:
    """Scan text for PII patterns. Returns list of findings."""
    findings: list[Finding] = []
    lines = text.splitlines()

    active_patterns = patterns_filter if patterns_filter else list(PATTERNS.keys())

    for line_num, line in enumerate(lines, start=1):
        for pattern_name in active_patterns:
            if pattern_name not in PATTERNS:
                continue
            regex = PATTERNS[pattern_name]["regex"]

            for match in re.finditer(regex, line):
                matched_text = match.group(0)

                if pattern_name == "CREDIT_CARD" and not luhn_check(matched_text):
                    continue

                if pattern_name == "CPF_RAW":
                    if not is_valid_cpf(matched_text):
                        continue

                if pattern_name == "CPF" and not is_valid_cpf(matched_text):
                    continue

                context = line.strip()[:100]
                findings.append(
                    Finding(
                        line=line_num,
                        pattern=pattern_name,
                        match=matched_text,
                        context=context,
                    )
                )

    return findings


def format_report(findings: list[Finding], source: str, as_json: bool = False) -> str:
    """Format findings as a readable report."""
    if as_json:
        return json.dumps(
            {
                "file": source,
                "total_issues": len(findings),
                "findings": [asdict(f) for f in findings],
            },
            indent=2,
        )

    lines = [
        f"File: {source}",
        f"Issues found: {len(findings)}",
        "",
    ]

    if not findings:
        lines.append("✓ No PII patterns detected.")
    else:
        for f in findings:
            lines.append(f"Line {f.line}: [{f.pattern}] {f.match}")
            lines.append(f"  Context: {f.context}")
            lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Detect PII patterns in files or piped text."
    )
    parser.add_argument(
        "source",
        help="File path to scan, or '-' for stdin",
    )
    parser.add_argument(
        "--patterns",
        help="Comma-separated list of patterns to check (default: all)",
        default=None,
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )
    parser.add_argument(
        "--list-patterns",
        action="store_true",
        help="List available patterns and exit",
    )
    args = parser.parse_args()

    if args.list_patterns:
        print("Available patterns:")
        for name, config in PATTERNS.items():
            print(f"  {name}: {config['description']}")
        sys.exit(0)

    if args.source == "-":
        text = sys.stdin.read()
        source = "stdin"
    else:
        path = Path(args.source)
        if not path.exists():
            print(f"Error: File not found: {args.source}", file=sys.stderr)
            sys.exit(1)
        text = path.read_text(encoding="utf-8", errors="replace")
        source = str(path)

    patterns_filter = None
    if args.patterns:
        patterns_filter = [p.strip().upper() for p in args.patterns.split(",")]

    findings = scan_text(text, patterns_filter)
    print(format_report(findings, source, as_json=args.json))

    sys.exit(0 if not findings else 1)


if __name__ == "__main__":
    main()
