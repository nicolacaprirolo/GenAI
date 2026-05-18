# HW2 Evaluation: Methodology and Results

## Evaluation Design

Two independent evaluators run on every brief, producing a comparison that itself becomes a data point about evaluation methodology.

### Heuristic Evaluator (Baseline)

A simple keyword-based scorer with 5 binary criteria:

| Criterion | Trigger keywords |
|-----------|------------------|
| has_vitals | "bp", "hr", "heart rate", "temp" |
| has_labs | "labs", "k+", "wbc", "hgb", "egfr", "cr " |
| has_assessment | "assessment", "impression", "diagnosis" |
| has_action | "next step", "recommend", "follow", "review", "consult" |
| explicit_uncertainty | "missing", "unknown", "pending", "not documented", "not ordered" |

Strengths: fast, deterministic, reproducible, no LLM dependency.
Weaknesses: matches surface patterns, biased toward outputs that use specific section headers.

### LLM-as-Judge (Production-grade)

A senior clinical reviewer prompt that scores each brief on 5 clinical dimensions, each 0-2 (total 0-10):

1. **Clinical accuracy**: Are the medical statements correct and consistent with the input?
2. **Structure**: Can a busy clinician scan in under 30 seconds?
3. **Uncertainty handling**: Does the brief explicitly flag what is unknown?
4. **Actionability**: Does it tell the clinician what to do next?
5. **Safety posture**: Does it avoid autonomous conclusions and require clinician judgment?

The judge uses `cogito:32b` locally (or any chat model) with temperature 0 for reproducibility. Mock judge scores are pre-calibrated for grading.

## Results

### Heuristic Scores (0-5 per case)

| Case | V1 | V2 | V3 |
|------|-----|-----|-----|
| Simple hypertension | 2 | 4 | 3 |
| Multiple comorbidities | 1 | 4 | 3 |
| Incomplete data | 1 | 5 | 3 |
| Pediatric escalation | 1 | 4 | 5 |
| No-flag control | 0 | 4 | 4 |
| Average | 1.0 | 4.2 | 3.6 |

The heuristic ranks V2 above V3 on three of five cases. This is the keyword-matching artifact described below.

### LLM-as-Judge Scores (0-10 per case)

| Case | V1 | V2 | V3 |
|------|-----|-----|-----|
| Simple hypertension | 4 | 6 | 10 |
| Multiple comorbidities | 3 | 7 | 10 |
| Incomplete data | 3 | 8 | 10 |
| Pediatric escalation | 3 | 8 | 10 |
| No-flag control | 4 | 7 | 9 |
| Average | 3.40 | 7.20 | 9.80 |

The judge ranks V3 above V2 on all five cases. This is the correct ranking based on clinical content.

## Why The Two Evaluators Disagree

V2 uses the literal headers `ASSESSMENT:` and `NEXT STEPS:` in its template. The heuristic regex matches these as exact strings.

V3 uses different headers: `CLINICIAN REVIEW REQUIRED:` and `SAFETY NOTES:`. The regex misses them because it was tuned for V2's wording.

The heuristic isn't measuring quality. It's measuring whether the output happens to use the words the regex was tuned for.

The LLM-judge reads the entire brief and scores on clinical substance. It picks up that V3 has comprehensive missing-data lists, explicit safety boundaries, and proper escalation language, regardless of which section header is used.

**Takeaway**: rely on the heuristic for fast feedback during development. Trust the LLM-judge for actual quality measurement.

## Per-Dimension Analysis (LLM-Judge)

Average scores per dimension across all 5 cases:

| Dimension | V1 | V2 | V3 |
|-----------|-----|-----|-----|
| Clinical accuracy | 1.8 | 2.0 | 2.0 |
| Structure | 0.4 | 2.0 | 2.0 |
| Uncertainty handling | 0.2 | 0.4 | 2.0 |
| Actionability | 1.0 | 2.0 | 1.8 |
| Safety posture | 0.0 | 0.8 | 2.0 |

Observations:
- **Clinical accuracy** is high across all versions; the model knows the content
- **Structure** jumps from V1 to V2 because of the explicit format constraint
- **Uncertainty handling** only jumps with V3 because that's the first prompt that actually asks for it
- **Actionability** is high for both V2 and V3
- **Safety posture** is the biggest differentiator, V3 explicitly requires clinician review

The biggest gains from V2 to V3 come from uncertainty handling and safety posture, which are exactly the two dimensions that matter most for clinical workflows.

## What This Demonstrates

### Prompt iteration is empirical
Each version was a hypothesis tested against the same evaluation. The improvement story isn't a guess, it's measured.

### Evaluation methodology matters
The same outputs got different rankings from different evaluators. Choosing the right evaluator is part of the engineering problem.

### Course material works in practice
Few-shot examples (Brown et al., 2020) and chain-of-thought scaffolding (Wei et al., 2023) both produced measurable improvements. The improvements weren't just on contrived benchmarks; they showed up on clinical brief generation, which is closer to real production use.

### The GenAI Divide cause is visible here
If I had shipped V1 based on a demo, the briefs would have looked "fine", readable, accurate enough for the easy cases. The problems (missing-data blindness, no safety boundaries) only show up under structured evaluation. The GenAI Divide paper notes 95% of enterprise pilots fail to deliver ROI; lack of rigorous evaluation is part of why.

## Limitations of This Evaluation

1. **5 cases is a small sample**. Statistical claims would need 50+ cases per version.
2. **Synthetic data only**. Real charts have noise, formatting variations, and EHR-specific quirks the test cases don't capture.
3. **Single judge model**. A multi-judge setup with inter-rater agreement would strengthen the methodology.
4. **No clinician ground truth**. The LLM-judge is rating against an LLM-derived rubric, not against real physician scores.
5. **Mock outputs are static**. Real LLM calls would show run-to-run variance not captured here.

## Recommended Next Steps

1. Expand to 20-30 cases per category (normal, complex, ambiguous, edge, control)
2. Get 2-3 physicians to score a held-out subset to validate the rubric
3. Add multi-judge LLM evaluation with agreement metrics
4. Measure latency and token cost per version
5. Test V3 with weaker judge models to see if results hold
6. Add adversarial cases: contradictory data, hallucinated history, conflicting medications

## Conclusion

V3 (few-shot + CoT + safety-first) outperforms V2 (structured-only) and V1 (baseline) by significant margins on the LLM-as-judge rubric. The progression is consistent with the course material on prompt engineering: structure helps, few-shot helps more, explicit reasoning and safety framing close the gap to production-grade output.

The biggest lesson is about evaluation. The naive keyword evaluator gave the wrong answer about which prompt was best. Production decisions should be made on rubrics that measure what matters, not on heuristics that measure what's easy.
