#!/usr/bin/env python3
"""LLM-powered PII replacement.

After detect.py finds PII patterns, fix.py replaces each finding with a
synthetic value of the same type. CPFs are replaced with Luhn-valid synthetic
CPFs, emails with realistic but fake emails, phone numbers with valid-format
synthetic phones, etc.

Backends:
- live: LLM generates contextual synthetic replacements
- mock: deterministic synthetic generators (no LLM needed)
"""

import argparse
import json
import os
import random
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()

REPO_ROOT = Path(__file__).parent
DETECT_SCRIPT = REPO_ROOT / "detect.py"


def synthetic_cpf() -> str:
    """Generate a Luhn-valid synthetic CPF."""
    digits = [random.randint(0, 9) for _ in range(9)]

    def check_digit(nums: list[int], multipliers: list[int]) -> int:
        total = sum(n * m for n, m in zip(nums, multipliers))
        remainder = total % 11
        return 0 if remainder < 2 else 11 - remainder

    d1 = check_digit(digits, list(range(10, 1, -1)))
    digits.append(d1)
    d2 = check_digit(digits, list(range(11, 1, -1)))
    digits.append(d2)
    s = "".join(str(d) for d in digits)
    return f"{s[:3]}.{s[3:6]}.{s[6:9]}-{s[9:]}"


def synthetic_email() -> str:
    """Generate a fake email at example.com."""
    return f"synthetic{random.randint(1000, 9999)}@example.com"


def synthetic_phone_br() -> str:
    """Generate a synthetic Brazilian phone number."""
    area = random.randint(11, 99)
    middle = random.randint(90000, 99999)
    end = random.randint(1000, 9999)
    return f"({area}) {middle}-{end}"


def synthetic_phone_us() -> str:
    """Generate a synthetic US phone number using 555-prefix (reserved for fiction)."""
    area = random.randint(200, 999)
    middle = 555
    end = random.randint(100, 199)
    return f"({area}) {middle}-0{end:03d}"


def synthetic_ssn() -> str:
    """Generate a fake SSN starting with 900 (not assigned, safe placeholder)."""
    return f"9{random.randint(0, 99):02d}-{random.randint(10, 99)}-{random.randint(1000, 9999)}"


def synthetic_dob() -> str:
    """Generate a fake date of birth."""
    day = random.randint(1, 28)
    month = random.randint(1, 12)
    year = random.randint(1950, 2000)
    return f"{day:02d}/{month:02d}/{year}"


def synthetic_credit_card() -> str:
    """Generate a fake Luhn-valid credit card."""
    digits = [4, 5, 3, 2, 0, 1, 5, 1, 1, 2, 8, 3, 0, 3, 6, 6]
    return "".join(str(d) for d in digits)


def synthetic_api_key() -> str:
    """Generate a fake API key placeholder."""
    return "sk-test_REDACTED_synthetic_key_for_testing_only"


SYNTHETIC_GENERATORS = {
    "CPF": synthetic_cpf,
    "CPF_RAW": lambda: synthetic_cpf().replace(".", "").replace("-", ""),
    "EMAIL": synthetic_email,
    "PHONE_BR": synthetic_phone_br,
    "PHONE_US": synthetic_phone_us,
    "SSN": synthetic_ssn,
    "DATE_OF_BIRTH": synthetic_dob,
    "CREDIT_CARD": synthetic_credit_card,
    "API_KEY": synthetic_api_key,
    "CNS": lambda: "111 1111 1111 1111",
}


def run_pattern_detection(source_path: Path) -> dict[str, Any]:
    """Call detect.py and parse JSON output."""
    result = subprocess.run(
        [sys.executable, str(DETECT_SCRIPT), "--json", str(source_path)],
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def apply_replacements(text: str, findings: list[dict[str, Any]], use_llm: bool, model: str, base_url: str) -> tuple[str, list[dict[str, Any]]]:
    """Replace each PII finding with a synthetic equivalent.

    Returns the cleaned text and the list of replacement records.
    """
    replacements: list[dict[str, Any]] = []
    replaced_text = text

    sorted_findings = sorted(findings, key=lambda f: len(f.get("match", "")), reverse=True)

    for finding in sorted_findings:
        pattern_type = finding.get("pattern", "UNKNOWN")
        original = finding.get("match", "")
        if not original:
            continue

        if use_llm:
            try:
                synthetic = generate_with_llm(pattern_type, original, model, base_url)
            except Exception:
                synthetic = SYNTHETIC_GENERATORS.get(pattern_type, lambda: "[REDACTED]")()
        else:
            synthetic = SYNTHETIC_GENERATORS.get(pattern_type, lambda: "[REDACTED]")()

        if original in replaced_text:
            replaced_text = replaced_text.replace(original, synthetic)
            replacements.append({
                "pattern": pattern_type,
                "original": original,
                "synthetic": synthetic,
            })

    return replaced_text, replacements


def generate_with_llm(pattern_type: str, original: str, model: str, base_url: str) -> str:
    """Use LLM to generate a context-appropriate synthetic replacement."""
    from openai import OpenAI

    client = OpenAI(base_url=base_url, api_key=os.getenv("LLM_API_KEY", "ollama"))
    prompt = (
        f"Generate a single synthetic replacement for a {pattern_type} that has the same format "
        f"as this example: {original}. Return only the synthetic value, no other text. "
        f"The synthetic value must be clearly fake (use 555-prefixes for US phones, example.com for emails, etc.)."
    )
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You generate synthetic PII replacements that match the format of the original."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=80,
        temperature=0.3,
    )
    raw = (response.choices[0].message.content or "").strip()
    raw = re.sub(r"^[`'\"]+|[`'\"]+$", "", raw).strip()
    return raw if raw else SYNTHETIC_GENERATORS.get(pattern_type, lambda: "[REDACTED]")()


def main():
    parser = argparse.ArgumentParser(description="Replace PII with synthetic values.")
    parser.add_argument("source", help="File to clean")
    parser.add_argument("--llm", action="store_true", help="Use LLM for replacement (vs deterministic)")
    parser.add_argument("--model", default="devstral:latest", help="LLM model for replacement")
    parser.add_argument("--base-url", default="http://localhost:11434/v1", help="OpenAI-compatible base URL")
    parser.add_argument("--in-place", action="store_true", help="Overwrite the source file")
    parser.add_argument("--output", help="Write cleaned content to this path (default: <source>.cleaned)")
    args = parser.parse_args()

    source_path = Path(args.source)
    if not source_path.exists():
        print(f"ERROR: file not found: {args.source}", file=sys.stderr)
        sys.exit(1)

    random.seed(42)

    print(f"Scanning {source_path} for PII patterns...")
    detection = run_pattern_detection(source_path)
    findings = detection.get("findings", [])
    print(f"Found {len(findings)} pattern matches.")

    if not findings:
        print("Nothing to replace.")
        sys.exit(0)

    text = source_path.read_text(encoding="utf-8", errors="replace")
    cleaned, replacements = apply_replacements(text, findings, args.llm, args.model, args.base_url)

    if args.in_place:
        out_path = source_path
    elif args.output:
        out_path = Path(args.output)
    else:
        out_path = source_path.with_suffix(source_path.suffix + ".cleaned")

    out_path.write_text(cleaned, encoding="utf-8")
    print(f"\nCleaned file written to: {out_path}")
    print(f"\nReplacements ({len(replacements)}):")
    for r in replacements:
        print(f"  [{r['pattern']}] {r['original']!r} -> {r['synthetic']!r}")


if __name__ == "__main__":
    main()
