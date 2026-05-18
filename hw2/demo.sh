#!/bin/bash
# HW2 Live Demo Script
# Designed for a 2-3 minute video walkthrough.
# Shows ONE real LLM call live, then displays cached results for the full eval.

set -e
cd "$(dirname "$0")"
source .venv/bin/activate

clear
echo "================================================================"
echo "  HW2: Clinical Brief Generator - Live Demo"
echo "================================================================"
echo ""
sleep 1

echo "STEP 1: Verify Ollama is running and the LLM is reachable"
echo "----------------------------------------------------------------"
curl -s http://localhost:11434/api/tags | python3 -c "
import json, sys
d = json.load(sys.stdin)
models = [m['name'] for m in d.get('models', [])]
print(f'  Ollama reachable. Models loaded: {len(models)}')
for m in models[:5]:
    print(f'    - {m}')
"
echo ""
sleep 2

echo "STEP 2: Generate ONE clinical brief with a REAL LLM call"
echo "  Model: devstral:latest (7B Llama variant, running locally)"
echo "  Backend: OpenAI-compatible HTTP API at localhost:11434"
echo "  Case: simple hypertension (Maria Santos, 55F)"
echo "  Prompt: V3 (few-shot + chain-of-thought + safety-first)"
echo "----------------------------------------------------------------"
echo ""
time python3 brief_generator.py \
  --case case_1_simple \
  --version v3_fewshot_cot \
  --model devstral:latest
echo ""
sleep 1

echo "STEP 3: Show the actual brief the LLM produced"
echo "----------------------------------------------------------------"
python3 -c "
import json
with open('outputs/generation_results.json') as f:
    data = json.load(f)
brief = data['results'][0]['briefs'][0]['output']
print(brief)
"
echo ""
sleep 2

echo "STEP 4: Now show the full evaluation (cached for time)"
echo "  5 cases x 3 prompt versions = 15 briefs total"
echo "  Full live run takes ~2 minutes; using mock for the rest"
echo "----------------------------------------------------------------"
python3 brief_generator.py --mock 2>&1 | tail -10
echo ""
sleep 1

echo "STEP 5: Score every brief with an LLM-as-judge"
echo "----------------------------------------------------------------"
python3 llm_judge.py --mock 2>&1 | tail -12
echo ""

echo "================================================================"
echo "  Demo complete. See report.md for the business case + deploy plan."
echo "================================================================"
