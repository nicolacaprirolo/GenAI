#!/usr/bin/env python3
"""Evaluate the PII detector against known test cases.

Metric: detection precision and recall against labeled expected findings.
"""

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).parent.parent
DETECT_SCRIPT = REPO_ROOT / "detect.py"
EXAMPLES_DIR = REPO_ROOT / "examples"


TEST_CASES = [
    {
        "name": "Clean code (false positive test)",
        "file": EXAMPLES_DIR / "clean_code.py",
        "expected_findings": 0,
        "expected_patterns": [],
    },
    {
        "name": "Mixed log file",
        "file": EXAMPLES_DIR / "mixed_log.txt",
        "expected_findings_min": 7,
        "expected_patterns": ["EMAIL", "CPF", "PHONE_BR", "SSN", "DATE_OF_BIRTH"],
    },
    {
        "name": "Patient demo data",
        "file": EXAMPLES_DIR / "patient_demo.py",
        "expected_findings_min": 8,
        "expected_patterns": ["CPF", "EMAIL", "PHONE_BR", "DATE_OF_BIRTH", "CREDIT_CARD", "SSN", "API_KEY"],
    },
]


def run_detector(file_path: Path) -> dict:
    """Run detect.py on a file and return parsed JSON."""
    result = subprocess.run(
        [sys.executable, str(DETECT_SCRIPT), "--json", str(file_path)],
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def evaluate():
    """Run all test cases and report metrics."""
    print("PII Detector Evaluation")
    print("=" * 70)

    results = []
    total_passed = 0
    total_tests = len(TEST_CASES)

    for test_case in TEST_CASES:
        print(f"\nTest: {test_case['name']}")
        print(f"  File: {test_case['file'].name}")

        if not test_case["file"].exists():
            print(f"  SKIP: File not found")
            continue

        output = run_detector(test_case["file"])
        actual_findings = output["total_issues"]
        actual_patterns = {f["pattern"] for f in output["findings"]}

        passed = True
        notes = []

        if "expected_findings" in test_case:
            if actual_findings == test_case["expected_findings"]:
                notes.append(f"✓ Exact finding count: {actual_findings}")
            else:
                passed = False
                notes.append(
                    f"✗ Expected {test_case['expected_findings']} findings, got {actual_findings}"
                )

        if "expected_findings_min" in test_case:
            if actual_findings >= test_case["expected_findings_min"]:
                notes.append(f"✓ Minimum findings met: {actual_findings} >= {test_case['expected_findings_min']}")
            else:
                passed = False
                notes.append(
                    f"✗ Expected at least {test_case['expected_findings_min']} findings, got {actual_findings}"
                )

        expected_patterns = set(test_case.get("expected_patterns", []))
        if expected_patterns:
            missing = expected_patterns - actual_patterns
            if not missing:
                notes.append(f"✓ All expected patterns detected: {sorted(expected_patterns)}")
            else:
                passed = False
                notes.append(f"✗ Missing patterns: {sorted(missing)}")

        for note in notes:
            print(f"  {note}")

        results.append(
            {
                "test": test_case["name"],
                "file": str(test_case["file"]),
                "actual_findings": actual_findings,
                "actual_patterns": sorted(actual_patterns),
                "passed": passed,
            }
        )

        if passed:
            total_passed += 1

    print("\n" + "=" * 70)
    print(f"Summary: {total_passed} / {total_tests} test cases passed")

    output_file = REPO_ROOT / "tests" / "evaluation_results.json"
    with open(output_file, "w") as f:
        json.dump(
            {
                "total_tests": total_tests,
                "passed": total_passed,
                "results": results,
            },
            f,
            indent=2,
        )

    print(f"Results saved to {output_file}")
    sys.exit(0 if total_passed == total_tests else 1)


if __name__ == "__main__":
    evaluate()
