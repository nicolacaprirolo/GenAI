#!/usr/bin/env python3
"""HW2 entry point.

Thin wrapper around brief_generator.py and llm_judge.py so the grader
can run a single command per the rubric.

Usage:
    python3 app.py                  # generate briefs + run judge (mock by default)
    python3 app.py --live           # use Ollama for both steps
    python3 app.py --generate-only  # just produce briefs
    python3 app.py --judge-only     # judge existing briefs
"""

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent


def run(cmd: list[str]) -> int:
    """Run a subprocess and stream its output. Return exit code."""
    print(f"\n$ {' '.join(cmd)}\n")
    return subprocess.call(cmd, cwd=ROOT)


def main():
    parser = argparse.ArgumentParser(description="HW2 brief generator + LLM judge runner.")
    parser.add_argument("--live", action="store_true", help="Use Ollama for real LLM calls")
    parser.add_argument("--generate-only", action="store_true", help="Only run brief generation")
    parser.add_argument("--judge-only", action="store_true", help="Only run judge")
    parser.add_argument("--model", default="devstral:latest", help="Model for brief generation")
    parser.add_argument("--judge-model", default="cogito:32b", help="Model for judging")
    args = parser.parse_args()

    mock_flag = [] if args.live else ["--mock"]

    if not args.judge_only:
        gen_cmd = [sys.executable, "brief_generator.py", "--model", args.model] + mock_flag
        rc = run(gen_cmd)
        if rc != 0:
            print(f"\nbrief_generator.py exited with code {rc}", file=sys.stderr)
            sys.exit(rc)

    if not args.generate_only:
        judge_cmd = [sys.executable, "llm_judge.py", "--judge-model", args.judge_model] + mock_flag
        rc = run(judge_cmd)
        if rc != 0:
            print(f"\nllm_judge.py exited with code {rc}", file=sys.stderr)
            sys.exit(rc)

    print("\n[done] Outputs in hw2/outputs/")
    print("       generation_results.json -> per-case briefs across V1/V2/V3")
    print("       judge_results.json      -> LLM-as-judge scores on 5 dimensions")


if __name__ == "__main__":
    main()
