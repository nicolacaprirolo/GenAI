#!/bin/bash
# HW4 Live Demo Script
# Designed for a 45-90 second video walkthrough.
# Runs the three required prompts: normal, edge, cautious.

set -e
cd "$(dirname "$0")"

clear
echo "================================================================"
echo "  HW4: PII Detector Skill - Live Demo"
echo "================================================================"
echo ""
sleep 1

echo "STEP 1: Show skill folder structure"
echo "----------------------------------------------------------------"
find .claude -type f
echo ""
sleep 2

echo "STEP 2: NORMAL CASE - scan patient demo file"
echo "  Expected: 13 PII findings with check-digit validation"
echo "----------------------------------------------------------------"
python3 .claude/skills/pii-detector/scripts/detect.py examples/patient_demo.py | head -25
echo ""
sleep 2

echo "STEP 3: EDGE CASE - LLM semantic detection on narrative text"
echo "  Expected: 4 semantic findings (name, address, contextual ID, minor)"
echo "----------------------------------------------------------------"
python3 .claude/skills/pii-detector/scripts/semantic_detector.py --mock examples/patient_narrative.txt
echo ""
sleep 2

echo "STEP 4: CAUTIOUS CASE - negative test (should NOT flag templates)"
echo "  Expected: 0 findings; all-zeros filter excludes obvious templates"
echo "----------------------------------------------------------------"
python3 .claude/skills/pii-detector/scripts/detect.py examples/version_string_traps.py
echo ""
sleep 2

echo "STEP 5: Evaluation against labeled ground truth"
echo "  Expected: P=R=F1=1.0 across all 4 test files"
echo "----------------------------------------------------------------"
python3 tests/evaluate.py 2>&1 | tail -10
echo ""

echo "================================================================"
echo "  Demo complete. Skill is reusable; drop .claude/skills/ into"
echo "  any project and Claude Code picks it up automatically."
echo "================================================================"
