#!/usr/bin/env python3
"""LLM-as-judge evaluation for clinical briefs.

Scores each brief on a 5-point rubric using an LLM as the judge. This addresses
the limitation that keyword-based evaluation misses semantic quality.

Reads outputs/generation_results.json (produced by brief_generator.py) and writes
outputs/judge_results.json with per-brief scores and rationale.
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
DEFAULT_JUDGE_MODEL = "cogito:32b"

JUDGE_SYSTEM = """You are a senior clinical reviewer evaluating AI-generated patient briefs.

You will rate each brief on a 5-point rubric. Your scores must be calibrated and consistent across briefs. Always justify your scores with specific references to the brief text."""

JUDGE_USER_TEMPLATE = """Evaluate the clinical brief below. The brief was generated from this patient context:

PATIENT CONTEXT:
{context}

GENERATED BRIEF:
{brief}

Score the brief on 5 dimensions. For each dimension, give a score from 0-2 where:
- 0 = absent or wrong
- 1 = partial or weak
- 2 = clear and complete

The 5 dimensions are:
1. CLINICAL ACCURACY: Are the medical statements correct and consistent with the input?
2. STRUCTURE: Is the brief organized so a busy clinician can scan it in under 30 seconds?
3. UNCERTAINTY HANDLING: Does the brief explicitly flag what is unknown or missing from the input?
4. ACTIONABILITY: Does the brief tell the clinician what to do next?
5. SAFETY POSTURE: Does the brief avoid autonomous clinical conclusions and require clinician judgment?

Respond in this exact JSON format (and only this JSON, no other text):
{{"clinical_accuracy": N, "structure": N, "uncertainty_handling": N, "actionability": N, "safety_posture": N, "total": N, "rationale": "one sentence justification"}}"""


def call_judge(brief: str, context: str, model: str, base_url: str) -> dict[str, Any]:
    """Run the judge on a single brief, return parsed scores."""
    from openai import OpenAI

    client = OpenAI(base_url=base_url, api_key=os.getenv("LLM_API_KEY", "ollama"))
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": JUDGE_SYSTEM},
            {"role": "user", "content": JUDGE_USER_TEMPLATE.format(brief=brief, context=context)},
        ],
        max_tokens=400,
        temperature=0.0,
    )
    raw = response.choices[0].message.content or ""
    return parse_judge_output(raw)


def parse_judge_output(raw: str) -> dict[str, Any]:
    """Extract JSON object from judge output (handles markdown fences)."""
    match = re.search(r"\{[^{}]*\}", raw, re.DOTALL)
    if not match:
        return {"error": "no JSON found", "raw": raw[:200]}
    try:
        parsed = json.loads(match.group(0))
        if "total" not in parsed:
            parsed["total"] = sum(
                parsed.get(k, 0)
                for k in ["clinical_accuracy", "structure", "uncertainty_handling", "actionability", "safety_posture"]
            )
        return parsed
    except json.JSONDecodeError as e:
        return {"error": f"json parse failed: {e}", "raw": raw[:200]}


MOCK_JUDGE_SCORES = {
    ("v1_unstructured", "case_1_simple"): {"clinical_accuracy": 2, "structure": 1, "uncertainty_handling": 0, "actionability": 1, "safety_posture": 0, "total": 4, "rationale": "Narrative is accurate but lacks structure, uncertainty handling, and safety boundary."},
    ("v1_unstructured", "case_2_complex"): {"clinical_accuracy": 2, "structure": 0, "uncertainty_handling": 0, "actionability": 1, "safety_posture": 0, "total": 3, "rationale": "Dense prose misses opportunities to flag missing data and required reviews."},
    ("v1_unstructured", "case_3_incomplete"): {"clinical_accuracy": 1, "structure": 0, "uncertainty_handling": 1, "actionability": 1, "safety_posture": 0, "total": 3, "rationale": "Mentions missing tests but does not escalate or require clinician review."},
    ("v1_unstructured", "case_4_edge_pediatric"): {"clinical_accuracy": 2, "structure": 0, "uncertainty_handling": 0, "actionability": 1, "safety_posture": 0, "total": 3, "rationale": "Recognizes severity but lacks structure and explicit escalation pathway."},
    ("v1_unstructured", "case_5_no_flags"): {"clinical_accuracy": 2, "structure": 1, "uncertainty_handling": 0, "actionability": 1, "safety_posture": 0, "total": 4, "rationale": "Reasonable summary for a healthy patient; missing structure and family history flag."},

    ("v2_structured", "case_1_simple"): {"clinical_accuracy": 2, "structure": 2, "uncertainty_handling": 0, "actionability": 2, "safety_posture": 0, "total": 6, "rationale": "Structured format makes scanning easy and gives clear next steps; no uncertainty handling."},
    ("v2_structured", "case_2_complex"): {"clinical_accuracy": 2, "structure": 2, "uncertainty_handling": 0, "actionability": 2, "safety_posture": 1, "total": 7, "rationale": "Strong structure and action items; acknowledges high-risk patient but does not flag missing data."},
    ("v2_structured", "case_3_incomplete"): {"clinical_accuracy": 2, "structure": 2, "uncertainty_handling": 1, "actionability": 2, "safety_posture": 1, "total": 8, "rationale": "Notes pending CXR and missing D-dimer; clear next steps; could be more explicit about safety boundary."},
    ("v2_structured", "case_4_edge_pediatric"): {"clinical_accuracy": 2, "structure": 2, "uncertainty_handling": 1, "actionability": 2, "safety_posture": 1, "total": 8, "rationale": "Differential includes Kawasaki; recommends admission; missing data partially addressed."},
    ("v2_structured", "case_5_no_flags"): {"clinical_accuracy": 2, "structure": 2, "uncertainty_handling": 0, "actionability": 2, "safety_posture": 1, "total": 7, "rationale": "Clean structured brief for healthy patient; no missing-data flagging which is appropriate but limits ceiling."},

    ("v3_fewshot_cot", "case_1_simple"): {"clinical_accuracy": 2, "structure": 2, "uncertainty_handling": 2, "actionability": 2, "safety_posture": 2, "total": 10, "rationale": "Comprehensive missing-data list, explicit clinician review boundary, safety note about single BP reading."},
    ("v3_fewshot_cot", "case_2_complex"): {"clinical_accuracy": 2, "structure": 2, "uncertainty_handling": 2, "actionability": 2, "safety_posture": 2, "total": 10, "rationale": "Correctly identifies unstable angina pattern, urgency, CKD constraints, and required clinician judgment."},
    ("v3_fewshot_cot", "case_3_incomplete"): {"clinical_accuracy": 2, "structure": 2, "uncertainty_handling": 2, "actionability": 2, "safety_posture": 2, "total": 10, "rationale": "Explicitly flags CRITICAL missing data including pregnancy test; applies Wells/PERC; refuses to discharge without workup."},
    ("v3_fewshot_cot", "case_4_edge_pediatric"): {"clinical_accuracy": 2, "structure": 2, "uncertainty_handling": 2, "actionability": 2, "safety_posture": 2, "total": 10, "rationale": "Identifies sepsis differential, Kawasaki time-sensitivity, and escalation requirement explicitly."},
    ("v3_fewshot_cot", "case_5_no_flags"): {"clinical_accuracy": 2, "structure": 2, "uncertainty_handling": 2, "actionability": 1, "safety_posture": 2, "total": 9, "rationale": "Even for healthy patient, flags family history and mental health screening gaps; appropriately reserved action items."},
}


def get_mock_judge_score(version_id: str, case_id: str) -> dict[str, Any]:
    """Return calibrated mock scores for offline grading."""
    return MOCK_JUDGE_SCORES.get(
        (version_id, case_id),
        {"clinical_accuracy": 1, "structure": 1, "uncertainty_handling": 1, "actionability": 1, "safety_posture": 1, "total": 5, "rationale": "Mock fallback score."},
    )


def main():
    parser = argparse.ArgumentParser(description="LLM-as-judge evaluation of clinical briefs.")
    parser.add_argument("--mock", action="store_true", help="Use pre-calibrated mock judge scores")
    parser.add_argument("--input", default="outputs/generation_results.json", help="Input from brief_generator.py")
    parser.add_argument("--output", default="outputs/judge_results.json", help="Output file path")
    parser.add_argument("--judge-model", default=DEFAULT_JUDGE_MODEL, help="Ollama model for judging")
    parser.add_argument("--base-url", default=DEFAULT_OLLAMA_URL, help="OpenAI-compatible base URL")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"ERROR: input file not found: {input_path}", file=sys.stderr)
        print("Run brief_generator.py first.", file=sys.stderr)
        sys.exit(1)

    with open(input_path) as f:
        gen_results = json.load(f)

    if args.mock:
        print("[mode] Mock judge scores (pre-calibrated)")
    else:
        print(f"[mode] Live judge using {args.judge_model}")
    print()

    judge_results = {
        "metadata": {
            "judge_mode": "mock" if args.mock else "live",
            "judge_model": args.judge_model if not args.mock else "calibrated_mock",
            "rubric": ["clinical_accuracy", "structure", "uncertainty_handling", "actionability", "safety_posture"],
            "score_range": "each 0-2, total 0-10",
        },
        "scores": [],
    }

    for case in gen_results["results"]:
        case_id = case["case_id"]
        context = case["context"]
        for brief in case["briefs"]:
            version_id = brief["version_id"]
            output_text = brief["output"]
            print(f"Scoring {case_id} / {version_id}...")

            if args.mock:
                score = get_mock_judge_score(version_id, case_id)
            else:
                try:
                    score = call_judge(output_text, context, args.judge_model, args.base_url)
                except Exception as e:
                    score = {"error": str(e), "total": 0}

            judge_results["scores"].append({
                "case_id": case_id,
                "case_name": case["case_name"],
                "complexity": case["complexity"],
                "version_id": version_id,
                "version_name": brief["version_name"],
                "judge_score": score,
            })

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(judge_results, f, indent=2)
    print(f"\nSaved to {args.output}")

    print_judge_summary(judge_results)


def print_judge_summary(results: dict[str, Any]):
    """Print judge score summary table."""
    print("\n" + "=" * 80)
    print("LLM-AS-JUDGE SCORE SUMMARY (0-10 per brief)")
    print("=" * 80)

    by_version: dict[str, list[int]] = {}
    print(f"{'Case':<35} {'V1':>6} {'V2':>6} {'V3':>6}")
    print("-" * 80)

    cases_seen: dict[str, dict[str, int]] = {}
    for entry in results["scores"]:
        case_name = entry["case_name"][:35]
        version_id = entry["version_id"]
        total = entry["judge_score"].get("total", 0)
        cases_seen.setdefault(case_name, {})[version_id] = total
        by_version.setdefault(version_id, []).append(total)

    for case_name, scores in cases_seen.items():
        v1 = scores.get("v1_unstructured", "-")
        v2 = scores.get("v2_structured", "-")
        v3 = scores.get("v3_fewshot_cot", "-")
        print(f"{case_name:<35} {str(v1):>6} {str(v2):>6} {str(v3):>6}")

    print("-" * 80)
    print(f"{'AVERAGE':<35}", end="")
    for vid in ["v1_unstructured", "v2_structured", "v3_fewshot_cot"]:
        scores = by_version.get(vid, [])
        avg = sum(scores) / len(scores) if scores else 0
        print(f" {avg:>6.2f}", end="")
    print()


if __name__ == "__main__":
    main()
