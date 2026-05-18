#!/usr/bin/env python3
"""HW3 entry point.

Thin wrapper around math_agent.py so the grader can run a single command
per the rubric.

Usage:
    python3 agent.py                  # live ReAct (requires Ollama)
    python3 agent.py --mock           # offline grading mode
    python3 agent.py --no-tools       # baseline (no tools available)
    python3 agent.py --question q1    # run only one question
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent


def main():
    args = [sys.executable, str(ROOT / "math_agent.py")] + sys.argv[1:]
    print(f"$ {' '.join(args)}\n")
    sys.exit(subprocess.call(args, cwd=ROOT))


if __name__ == "__main__":
    main()
