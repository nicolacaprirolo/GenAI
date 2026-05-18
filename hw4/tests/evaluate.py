#!/usr/bin/env python3
"""Evaluate the PII detector with precision, recall, and F1 against labeled ground truth.

Ground truth is a hand-curated list of (line_number, pattern_type) tuples for each
test file. The evaluator compares the detector's findings against ground truth
and computes the three standard metrics.
"""

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).parent.parent
DETECT_SCRIPT = REPO_ROOT / ".claude" / "skills" / "pii-detector" / "scripts" / "detect.py"
EXAMPLES_DIR = REPO_ROOT / "examples"


GROUND_TRUTH = {
    "clean_code.py": {
        "expected": set(),
        "description": "No PII; tests false positive rate.",
    },
    "version_string_traps.py": {
        "expected": set(),
        "description": "Negative test: strings that look like PII but aren't (version, IDs, placeholders).",
    },
    "mixed_log.txt": {
        "expected": {
            (3, "EMAIL"),
            (4, "CPF"),
            (6, "PHONE_BR"),
            (7, "EMAIL"),
            (8, "SSN"),
            (9, "DATE_OF_BIRTH"),
            (10, "CNS"),
        },
        "description": "Server log with embedded PII mixed in normal log lines.",
    },
    "patient_demo.py": {
        "expected": {
            (10, "CPF"),
            (11, "EMAIL"),
            (12, "PHONE_BR"),
            (13, "DATE_OF_BIRTH"),
            (14, "SSN"),
            (18, "CPF"),
            (19, "EMAIL"),
            (20, "PHONE_BR"),
            (21, "DATE_OF_BIRTH"),
            (22, "CREDIT_CARD"),
            (30, "EMAIL"),
            (33, "API_KEY"),
            (34, "EMAIL"),
        },
        "description": "Dense PII test file with patterns across all detector categories.",
    },
}


def run_detector(file_path: Path) -> set[tuple[int, str]]:
    """Run detect.py and return findings as set of (line, pattern) tuples."""
    result = subprocess.run(
        [sys.executable, str(DETECT_SCRIPT), "--json", str(file_path)],
        capture_output=True,
        text=True,
    )
    output = json.loads(result.stdout)
    return {(f["line"], f["pattern"]) for f in output.get("findings", [])}


def compute_metrics(predicted: set, expected: set) -> dict[str, float]:
    """Compute precision, recall, F1, and confusion matrix counts."""
    true_positives = predicted & expected
    false_positives = predicted - expected
    false_negatives = expected - predicted

    tp = len(true_positives)
    fp = len(false_positives)
    fn = len(false_negatives)

    precision = tp / (tp + fp) if (tp + fp) > 0 else (1.0 if not expected else 0.0)
    recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
        "fp_items": sorted(false_positives),
        "fn_items": sorted(false_negatives),
    }


def evaluate():
    """Run all ground-truth comparisons and report metrics."""
    print("PII Detector Evaluation: Precision / Recall / F1")
    print("=" * 80)

    results = []
    all_tp = 0
    all_fp = 0
    all_fn = 0

    for filename, gt in GROUND_TRUTH.items():
        file_path = EXAMPLES_DIR / filename
        if not file_path.exists():
            print(f"SKIP: {filename} not found")
            continue

        print(f"\n--- {filename}")
        print(f"    {gt['description']}")

        predicted = run_detector(file_path)
        metrics = compute_metrics(predicted, gt["expected"])

        all_tp += metrics["true_positives"]
        all_fp += metrics["false_positives"]
        all_fn += metrics["false_negatives"]

        print(f"    Expected: {len(gt['expected'])} findings, Got: {len(predicted)}")
        print(f"    TP: {metrics['true_positives']}, FP: {metrics['false_positives']}, FN: {metrics['false_negatives']}")
        print(f"    Precision: {metrics['precision']}, Recall: {metrics['recall']}, F1: {metrics['f1']}")
        if metrics["fp_items"]:
            print(f"    False positives: {metrics['fp_items']}")
        if metrics["fn_items"]:
            print(f"    False negatives: {metrics['fn_items']}")

        results.append({
            "file": filename,
            "description": gt["description"],
            "expected_count": len(gt["expected"]),
            "predicted_count": len(predicted),
            "metrics": metrics,
        })

    overall_precision = all_tp / (all_tp + all_fp) if (all_tp + all_fp) > 0 else 0.0
    overall_recall = all_tp / (all_tp + all_fn) if (all_tp + all_fn) > 0 else 0.0
    overall_f1 = 2 * overall_precision * overall_recall / (overall_precision + overall_recall) if (overall_precision + overall_recall) > 0 else 0.0

    print("\n" + "=" * 80)
    print("OVERALL METRICS")
    print("=" * 80)
    print(f"  Total TP: {all_tp}")
    print(f"  Total FP: {all_fp}")
    print(f"  Total FN: {all_fn}")
    print(f"  Micro-Precision: {round(overall_precision, 3)}")
    print(f"  Micro-Recall:    {round(overall_recall, 3)}")
    print(f"  Micro-F1:        {round(overall_f1, 3)}")

    output_file = REPO_ROOT / "tests" / "evaluation_results.json"
    with open(output_file, "w") as f:
        json.dump({
            "per_file": results,
            "overall": {
                "true_positives": all_tp,
                "false_positives": all_fp,
                "false_negatives": all_fn,
                "precision": round(overall_precision, 3),
                "recall": round(overall_recall, 3),
                "f1": round(overall_f1, 3),
            },
        }, f, indent=2)

    print(f"\nResults saved to {output_file}")

    sys.exit(0 if (all_fp == 0 and all_fn == 0) else 1)


if __name__ == "__main__":
    evaluate()
