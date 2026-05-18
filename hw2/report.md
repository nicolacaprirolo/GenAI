# HW2 Report: Clinical Brief Generator

**Author**: Nicola Capriolo Teran
**Course**: BU.330.760.41, Generative AI in Business, Spring 2026
**Assignment**: HW2, Build and Evaluate a Simple GenAI Workflow

---

## 1. Business Case

Primary care clinicians in public hospitals across Brazil and other Latin American countries see 30 to 50 patients per shift. The Brazilian SUS system serves over 200 million people through a network of clinics where median visit time is under 10 minutes. Clinicians spend a meaningful fraction of that time scanning EHR notes to reconstruct the patient's situation before the visit can even begin.

Holi Labs (where I work) is building decision support tools for this market. Brief generation is one of the smallest, most repeatable workflows we can address. The hypothesis: if we can produce a 30-second structured pre-visit brief that surfaces what is relevant, what is missing, and what requires clinician judgment, we cut the cognitive load on each visit.

The financial story is straightforward. SUS clinicians cost roughly R$80 per hour of consulting time. If a brief saves 90 seconds per visit and a clinician sees 40 patients per shift, that is 60 minutes recovered per shift, R$80 per clinician per day. At Holi Labs' active footprint of ~600 clinicians, the implied annual recovery is ~R$11.5M of clinician time, even before accounting for reduced documentation errors and faster discharge throughput.

The risk story is also clear. A bad brief in clinical context is dangerous. A confident-sounding brief that omits a critical lab is worse than no brief at all. This makes evaluation methodology non-optional.

## 2. Model Choice

I tested with two local LLMs running through Ollama:

- `devstral:latest` (17GB, fast, 7B-class) for brief generation
- `cogito:32b` (Qwen2 family, 32B) for LLM-as-judge evaluation

These two were chosen because the workflow runs on the developer machine for prototyping. For production, the model selection would shift to a hosted API (Claude 3.7 Sonnet for the generator, GPT-4 or Claude as the judge) for latency and reliability. The architecture stays the same because both Ollama and the production APIs expose OpenAI-compatible endpoints; only the base URL changes.

Why not just use the largest available model and skip iteration? Because the GenAI Divide paper (Challapally et al., 2025) reports that 95 percent of enterprise pilots fail to deliver ROI, and one reason is teams reach for the biggest model and stop thinking about prompt design. A smaller well-prompted model often outperforms a larger badly-prompted model on the metrics the user cares about. This homework tests that hypothesis directly.

## 3. Baseline vs Final

Three prompt versions were tested on five synthetic patient cases. Each brief was scored by an LLM-as-judge on five clinical dimensions, each 0-2, total 0-10.

### Per-dimension averages (across all 5 cases)

| Dimension | V1 (baseline) | V2 (structured) | V3 (few-shot + CoT + safety) |
|-----------|---------------|-----------------|------------------------------|
| Clinical accuracy | 1.8 | 2.0 | 2.0 |
| Structure | 0.4 | 2.0 | 2.0 |
| Uncertainty handling | 0.2 | 0.4 | 2.0 |
| Actionability | 1.0 | 2.0 | 1.8 |
| Safety posture | 0.0 | 0.8 | 2.0 |
| **Total** | **3.40** | **7.20** | **9.80** |

### Per-case totals (0-10)

| Case | V1 | V2 | V3 | Delta V3 vs V1 |
|------|-----|-----|-----|----------------|
| Simple hypertension | 4 | 6 | 10 | +6 |
| Multiple comorbidities | 3 | 7 | 10 | +7 |
| Incomplete data | 3 | 8 | 10 | +7 |
| Pediatric escalation | 3 | 8 | 10 | +7 |
| Healthy control | 4 | 7 | 9 | +5 |

V3 outperforms V1 by 6.4 points on average and outperforms V2 by 2.6 points. The biggest delta is on uncertainty handling, where V3 jumped from 0.4 to 2.0. Safety posture moved from 0.8 to 2.0. These two dimensions are where the V2-to-V3 work paid off.

### Why V3 wins

V3 added three changes from V2, each grounded in a course reading:

1. Role reframing from "documentation assistant" to "clinical safety assistant"
2. Two complete few-shot examples in the Brown et al. (2020) style, showing what a good brief looks like
3. Explicit chain-of-thought REASONING step before the final OUTPUT, per the Wei et al. (2023) pattern

The few-shot examples acted as in-context training. The model saw "MISSING DATA: lipid panel, urine ACR..." in the examples and started producing similar lists on new inputs. The CoT scaffolding forced the model to surface concerns it would otherwise have skipped. The safety framing oriented the model toward escalation rather than reassurance.

## 4. Where It Still Fails

The 9.80 average is high but not 10.0. Specific failure modes:

- **Case 5 (healthy patient) lost 1 point on actionability.** The judge expected more concrete action items, but in reality a healthy 32-year-old does not need a long action list. This is a rubric calibration issue more than a generator failure.
- **Alert fatigue risk.** V3 outputs "CLINICIAN REVIEW REQUIRED: Yes" on every case. In a production environment where this fires 40 times per shift, clinicians will start ignoring it. A future version needs a graded urgency level (low / medium / urgent) rather than binary.
- **Token cost.** V3 prompts are roughly 6x longer than V1 due to the two embedded few-shot examples. At hosted API pricing this matters at scale. A production version should compress the examples or switch to embedding-based example selection.
- **Synthetic data only.** All 5 test cases are hand-written. Real EHR text has artifacts (typos, copy-paste duplication, abbreviations, mixed Portuguese-English) that this evaluation does not stress. The first real-world test will likely surface failure modes the synthetic set never hit.
- **Single judge model.** The LLM-as-judge is itself an LLM with its own biases. A multi-judge setup with inter-rater agreement would be more credible. A real validation would also include 2-3 physicians scoring a held-out set blinded.
- **Keyword evaluation disagreed with the judge.** The same outputs ranked V2 above V3 under the heuristic evaluator because V2 used the literal word "ASSESSMENT" that the regex matched. This is itself a finding: lightweight evaluators give the wrong answer when they don't measure what matters.

## 5. Deploy Recommendation

I would deploy V3 to internal pilot with the following conditions:

1. **Closed pilot first.** Run on 3 partner clinics, 5 clinicians each, for 4 weeks. Compare clinician satisfaction and visit throughput against a matched control group. Do not push to production-wide until pilot data supports it.

2. **Add graded urgency.** Replace the binary "CLINICIAN REVIEW REQUIRED" with three levels (routine / review-recommended / urgent). This requires updating both the prompt and the LLM-judge rubric.

3. **Real EHR data validation.** Before production, score V3 against 50 real (de-identified) EHR notes scored by 3 physicians. This is the validation step that prevents shipping a tool that works on synthetic data and fails on real data.

4. **Two-LLM voting on safety-critical cases.** For any brief that scores high urgency, run a second model independently and surface both outputs to the clinician. Disagreement between models is itself a useful signal.

5. **Audit logging.** Every brief generated should be logged with the input context, the model output, the clinician's acceptance/edit decision, and the eventual visit outcome. This is the data we need to retrain or refine the prompt over time.

6. **Token budget monitoring.** V3 at scale could cost meaningful money. Set per-clinician daily budgets and circuit breakers.

7. **Do not ship V1 or V2.** V1 has unacceptable safety posture (score 0.0 average). V2 has unacceptable uncertainty handling (0.4). Both would create false confidence that introduces clinical risk.

### Estimated Pilot Cost (4 weeks, 3 clinics)

- 15 clinicians × 40 visits/day × 20 working days = 12,000 briefs
- V3 average prompt + completion = ~3000 tokens at $3/1M tokens (Claude Sonnet pricing)
- Total pilot LLM cost: ~$108
- Plus eval cost (LLM-as-judge on a sample): ~$30
- Total: under $200 for the pilot

The cost is trivial compared to the clinician-hour recovery if the pilot validates. The risk is upside: we either confirm the value proposition or learn fast what is missing.

## 6. Summary

V3 outperforms V1 by 6.4 points on the LLM-judge rubric, with the largest gains on safety posture and uncertainty handling. The improvement was achieved by combining course material (few-shot examples and chain-of-thought scaffolding) with a deliberate role reframing toward safety. Deployment is recommended as a closed pilot with the conditions listed above, particularly graded urgency and real-EHR validation before production rollout.

The bigger lesson: prompt engineering with rigorous evaluation produces measurable, reproducible improvements. The first version that "worked" (V1) would have looked fine in a demo and failed in production. Catching that failure in evaluation rather than in a clinic is the work that turns a prototype into a useful product.

---

**Repo**: github.com/[username]/[repo]
**Demo video**: [link to be added after recording]
**Last updated**: 2026-05-18
