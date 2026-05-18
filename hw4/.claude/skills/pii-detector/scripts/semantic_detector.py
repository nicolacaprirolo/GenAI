#!/usr/bin/env python3
"""LLM-based semantic PII detector.

Augments the regex-based detect.py with a layer that catches PII the regex
misses: names, addresses, free-text health information, and contextual PII.

Backends:
- live: real LLM call to local Ollama
- mock: pre-recorded findings for offline grading
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()

DEFAULT_OLLAMA_URL = "http://localhost:11434/v1"
DEFAULT_MODEL = "cogito:32b"


SEMANTIC_SYSTEM = """You are a PII (Personally Identifiable Information) detector.

You scan text for PII that regex patterns cannot catch:
- Person names (first + last, or just last with a title)
- Physical addresses (street, city, postal code patterns)
- Free-text health information attached to specific individuals (e.g., "Maria has diabetes")
- Contextual identifiers ("the patient in room 312", "John from accounting")
- Family relationships that identify minors ("his daughter Ana, age 8")

You do NOT flag:
- Generic terms (patient, doctor, hospital) without specific identifying context
- Public figures in clearly non-private contexts
- Sample/test data that is obviously synthetic
- Programming identifiers (variable names, function names)

For each finding, you provide: the exact text, the line number, the type, and a short explanation.

Respond in JSON only, no other text."""


SEMANTIC_USER_TEMPLATE = """Scan the following text for semantic PII (names, addresses, free-text health info, contextual identifiers).

Return findings as a JSON array. Each finding must have:
- "line": line number where the PII appears (1-indexed)
- "type": one of NAME, ADDRESS, HEALTH_INFO, CONTEXTUAL_ID
- "text": the exact PII text from the input
- "explanation": one sentence on why this is PII

If no semantic PII is found, return [].

Text to scan (lines are numbered for reference):
{numbered_text}

JSON array of findings:"""


MOCK_SEMANTIC_FINDINGS: dict[str, list[dict[str, Any]]] = {
    "patient_demo.py": [
        {"line": 9, "type": "NAME", "text": "Maria Santos", "explanation": "First and last name attached to patient record."},
        {"line": 17, "type": "NAME", "text": "João Silva", "explanation": "First and last name attached to patient record."},
    ],
    "mixed_log.txt": [],
    "clean_code.py": [],
    "patient_narrative.txt": [
        {"line": 1, "type": "NAME", "text": "Carlos Mendes", "explanation": "Patient first and last name."},
        {"line": 2, "type": "ADDRESS", "text": "Rua das Flores 123, São Paulo", "explanation": "Street address with city."},
        {"line": 3, "type": "HEALTH_INFO", "text": "Type 2 diabetes diagnosed in 2018", "explanation": "Specific health condition tied to named individual."},
        {"line": 6, "type": "CONTEXTUAL_ID", "text": "the patient in room 304", "explanation": "Room number plus context identifies a specific patient."},
    ],
    "version_string_traps.py": [],
}


def number_lines(text: str) -> str:
    """Prepend line numbers for the LLM."""
    return "\n".join(f"{i+1}: {line}" for i, line in enumerate(text.splitlines()))


def parse_findings(raw: str) -> list[dict[str, Any]]:
    """Extract JSON array from LLM response."""
    match = re.search(r"\[.*?\]", raw, re.DOTALL)
    if not match:
        return []
    try:
        parsed = json.loads(match.group(0))
        if not isinstance(parsed, list):
            return []
        return [item for item in parsed if isinstance(item, dict) and "line" in item and "type" in item]
    except json.JSONDecodeError:
        return []


def call_semantic_detector(text: str, model: str, base_url: str) -> list[dict[str, Any]]:
    """Call LLM to detect semantic PII."""
    from openai import OpenAI

    client = OpenAI(base_url=base_url, api_key=os.getenv("LLM_API_KEY", "ollama"))
    numbered = number_lines(text)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SEMANTIC_SYSTEM},
            {"role": "user", "content": SEMANTIC_USER_TEMPLATE.format(numbered_text=numbered)},
        ],
        max_tokens=600,
        temperature=0.0,
    )
    raw = response.choices[0].message.content or ""
    return parse_findings(raw)


def get_mock_findings(file_path: Path) -> list[dict[str, Any]]:
    """Look up pre-recorded findings by filename."""
    return MOCK_SEMANTIC_FINDINGS.get(file_path.name, [])


def detect_backend(mock_flag: bool, base_url: str) -> tuple[str, str]:
    if mock_flag:
        return ("mock", "Forced mock mode.")
    import urllib.request, urllib.error
    try:
        urllib.request.urlopen(base_url.replace("/v1", "/api/tags"), timeout=2)
        return ("live", f"Live semantic detection via {base_url}.")
    except (urllib.error.URLError, OSError):
        return ("mock", "No Ollama at base_url, using mock findings.")


def main():
    parser = argparse.ArgumentParser(description="LLM-based semantic PII detector.")
    parser.add_argument("source", help="File to scan, or '-' for stdin")
    parser.add_argument("--mock", action="store_true", help="Use pre-recorded findings")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="LLM model name")
    parser.add_argument("--base-url", default=DEFAULT_OLLAMA_URL, help="OpenAI-compatible base URL")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    mode, msg = detect_backend(args.mock, args.base_url)

    if args.source == "-":
        text = sys.stdin.read()
        source_name = "stdin"
        source_path = None
    else:
        source_path = Path(args.source)
        if not source_path.exists():
            print(f"ERROR: file not found: {args.source}", file=sys.stderr)
            sys.exit(1)
        text = source_path.read_text(encoding="utf-8", errors="replace")
        source_name = source_path.name

    if mode == "mock":
        findings = get_mock_findings(source_path) if source_path else []
    else:
        try:
            findings = call_semantic_detector(text, args.model, args.base_url)
        except Exception as e:
            print(f"ERROR: LLM call failed: {e}", file=sys.stderr)
            sys.exit(2)

    if args.json:
        print(json.dumps({
            "source": source_name,
            "mode": mode,
            "model": args.model if mode == "live" else "mock",
            "total_findings": len(findings),
            "findings": findings,
        }, indent=2))
    else:
        print(f"[mode] {msg}")
        print(f"File: {source_name}")
        print(f"Semantic findings: {len(findings)}")
        print()
        for f in findings:
            print(f"Line {f.get('line', '?')}: [{f.get('type', '?')}] {f.get('text', '?')}")
            print(f"  {f.get('explanation', '')}")
            print()

    sys.exit(0 if not findings else 1)


if __name__ == "__main__":
    main()
