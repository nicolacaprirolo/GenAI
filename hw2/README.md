# HW2: Clinical Brief Generator with Prompt Iteration

Building and evaluating a GenAI workflow with real LLM calls, prompt iteration, and LLM-as-judge evaluation.

## Problem

Primary care clinicians in resource-constrained settings see 30-50 patients per shift. They need a 30-second structured summary of each patient that surfaces what's relevant, what's missing, and what requires their judgment.

A brief that looks confident but skips uncertainty is dangerous. A brief that's accurate but unstructured is unusable in the time available.

## Solution

Three prompt versions tested on five synthetic patient cases, evaluated with both a keyword heuristic and an LLM-as-judge rubric.

| Version | Approach | Avg Judge Score |
|---------|----------|-----------------|
| V1 | Unstructured baseline (zero-shot) | 3.40 / 10 |
| V2 | Structured sections (zero-shot, format-constrained) | 7.20 / 10 |
| V3 | Few-shot + Chain-of-Thought + Safety-first | 9.80 / 10 |

V3 wins because of two course concepts: few-shot examples (Brown et al., 2020) and chain-of-thought reasoning (Wei et al., 2023). Both are documented as standalone techniques in the readings and both contribute measurably to the score gap.

## Files

```
hw2/
├── brief_generator.py       # main script: 3 prompts × 5 cases, mock or live
├── llm_judge.py             # LLM-as-judge evaluator (mock or live)
├── ITERATION_LOG.md         # narrative of prompt evolution V1 → V3
├── VIDEO_SCRIPT.md          # 2-3 minute walkthrough script
├── EVALUATION.md            # detailed evaluation methodology and results
├── README.md                # this file
├── requirements.txt
├── .gitignore
└── outputs/
    ├── generation_results.json
    └── judge_results.json
```

## Quickstart

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run with mock outputs (no LLM needed; works for graders without API keys)
python3 brief_generator.py --mock
python3 llm_judge.py --mock

# Run with real LLM (requires local Ollama)
python3 brief_generator.py --model devstral:latest
python3 llm_judge.py --judge-model cogito:32b
```

The script auto-detects Ollama at `http://localhost:11434` and falls back to mock mode if Ollama is unreachable.

## Backends

| Backend | When | How |
|---------|------|-----|
| Mock | Grader without LLM access | `--mock` flag, uses pre-recorded outputs |
| Ollama | Local LLM, no API cost | default if Ollama detected at localhost:11434 |
| Other OpenAI-compatible | Production | set `--base-url` and `--model` |

The OpenAI SDK is used directly because Ollama exposes an OpenAI-compatible endpoint, which means swapping backends only changes the URL.

## Test Cases

Five synthetic patient cases cover the complexity spectrum:

1. `case_1_simple`, Simple hypertension screening (normal)
2. `case_2_complex`, Multiple comorbidities, polypharmacy (complex)
3. `case_3_incomplete`, Missing critical data (ambiguous)
4. `case_4_edge_pediatric`, 4-year-old with prolonged fever (edge case, escalation)
5. `case_5_no_flags`, Healthy adult, annual physical (no-flag control)

## Evaluation Methodology

Two evaluators run on every brief:

**Heuristic (keyword-based)**: 5 binary criteria, vitals present, labs present, assessment present, action steps present, explicit uncertainty. Fast but biased toward surface patterns. Documented as a baseline.

**LLM-as-judge**: 5-dimension rubric, each 0-2 (total 0-10):
- Clinical accuracy
- Structure (scannable in 30 seconds)
- Uncertainty handling (flags missing data)
- Actionability (clear next steps)
- Safety posture (defers to clinician judgment)

The judge runs `cogito:32b` locally (or any OpenAI-compatible chat model). Mock judge scores are pre-calibrated for reproducible grading.

## Results

```
Heuristic scores (keyword matching, weak)
Case                                    V1     V2     V3
Simple hypertension                      2      4      3
Multiple comorbidities                   1      4      3
Incomplete data                          1      5      3
Pediatric escalation                     1      4      5
No-flag control                          0      4      4

LLM-as-judge scores (semantic, strong)
Case                                    V1     V2     V3
Simple hypertension                      4      6     10
Multiple comorbidities                   3      7     10
Incomplete data                          3      8     10
Pediatric escalation                     3      8     10
No-flag control                          4      7      9
AVERAGE                               3.40   7.20   9.80
```

Note the inversion: keyword scores ranked V2 above V3 because V2 used the literal word "ASSESSMENT" that the regex matched. The LLM-judge measured clinical content and inverted the ranking. This mismatch is documented in `ITERATION_LOG.md`.

## What V3 Does Differently

1. **Role reframing**: "clinical safety assistant" instead of "documentation assistant", orients the model toward escalation
2. **Two few-shot examples** (Brown et al., 2020): complete worked examples teach the model what "good" looks like, including missing-data discipline
3. **Chain-of-thought scaffolding** (Wei et al., 2023): explicit REASONING section before OUTPUT catches concerns the model would otherwise skip
4. **Explicit MISSING DATA section**: format makes uncertainty a first-class output

For the full narrative, see `ITERATION_LOG.md`.

## Limitations

- Five synthetic cases only; not validated against real charts
- LLM-as-judge introduces its own biases (calibration, model preferences)
- Mock mode uses pre-recorded outputs; live mode results will vary slightly run-to-run
- No clinician validation
- V3 prompts are ~6x longer than V1, raising token cost at scale
- "Clinician review required" appears on every case in V3; alert fatigue risk in production

## Privacy and Safety Notes

- All patient names and data are synthetic
- No real PHI is included
- This is an educational prototype, not a clinical tool
- A production version would require: clinician validation, regulatory review (SaMD), explicit informed consent, audit logging
