# HW2 Evaluation: Prompt Iteration Analysis

## Methodology

Three distinct prompt versions were tested on three patient cases of varying complexity. Each brief was evaluated against five criteria:

1. **has_vitals**: Vital signs (BP, HR, RR, temperature) included
2. **has_labs**: Laboratory values mentioned
3. **has_assessment**: Clinical impression or status assessment provided
4. **has_action**: Next steps or recommendations stated
5. **explicit_uncertainty**: Surfaces what is unknown or missing

Criteria were evaluated using keyword matching, which provides a simple quantitative measure but lacks clinical expertise. A human reviewer would catch nuance the keyword approach misses.

## Results Summary

### V1: Unstructured Narrative (Baseline)

Performance:
- Simple case: 3/5 criteria met
- Complex case: 3/5 criteria met  
- Incomplete case: 4/5 criteria met
- Average: 3.3/5 (66%)

Strengths:
- Flows naturally, readable for clinicians
- Includes reasoning and context

Weaknesses:
- Assessment section frequently skipped (only 1/3 cases)
- Lacks systematic structure, easy to overlook data
- Minimal explicit acknowledgment of uncertainty

### V2: Structured with Sections

Performance:
- Simple case: 4/5 criteria met
- Complex case: 4/5 criteria met
- Incomplete case: 5/5 criteria met
- Average: 4.3/5 (86%)

Strengths:
- Guaranteed coverage of key information categories
- Assessment section always present
- Easy for systems to parse and validate
- Next steps explicitly labeled

Weaknesses:
- Formulaic, may feel rigid to clinicians
- Doesn't naturally surface uncertainty
- Can create false sense of completeness when data is missing

### V3: Safety-First (Production)

Performance:
- Simple case: 5/5 criteria met
- Complex case: 5/5 criteria met
- Incomplete case: 5/5 criteria met
- Average: 5/5 (100%)

Strengths:
- Explicitly surfaces missing data in every case
- Clinician review boundary always clear
- Surfaces drug interactions and safety concerns
- Highest evaluation score across all test cases
- Supports human oversight

Weaknesses:
- Longer, more verbose than other versions
- May create alert fatigue if overused
- Requires clinician engagement on every case

## Key Finding

V3 (Safety-First) met all evaluation criteria in all test cases. This version prioritizes uncertainty and clinician review requirements, producing the most safety-conscious output.

Comparing V1 and V2: V2 adds 1.3 criteria on average due to explicit structure. However, V2 still falls short on explicit_uncertainty. V3 combines structured format (like V2) with explicit uncertainty handling (which V1 and V2 lack).

## Interpretation

For clinical workflows, prompt design dramatically affects information quality. A simple instruction produces readable but incomplete output. Adding structure improves completeness but doesn't address the critical safety requirement of surfacing uncertainty. Only when the prompt explicitly instructs the model to surface missing data and clinician review requirements does full criteria coverage emerge.

This finding reflects foundational course material on few-shot learning and prompt engineering. The few-shot learning paper emphasizes that in-context examples shape model behavior. Here, the prompt structure itself acts as a form of in-context learning: explicit instructions produce explicit compliance.

## Limitations

- Keyword-based evaluation is crude and misses clinical subtlety
- Mock outputs demonstrate the concept but lack variability from real LLM responses
- Three test cases is a small sample; broader evaluation would strengthen claims
- Clinical experts would disagree with some keyword mappings
- Real prompts might include few-shot examples or chain-of-thought structures for better performance

## Recommendations for Production

If deployed clinically, V3 (Safety-First) would be the starting point. However:

- Test with real patient cases and clinical expert review
- Measure information completeness alongside clinician trust and adoption
- Monitor for alert fatigue if all briefs flag "clinician review required"
- Consider a hybrid approach: V3 for high-risk cases, V2 for routine cases
- Add guardrails to prevent hallucinated drug interactions or safety concerns
- Require clinician signoff before any treatment recommendation

## Conclusion

Prompt iteration reveals that structure improves coverage, and explicit uncertainty handling improves safety. The progression from V1 (unstructured) through V2 (structured) to V3 (safety-first) demonstrates how prompt design trades off readability for completeness and safety.

This workflow embodies the course philosophy: pick a problem, prototype multiple approaches, evaluate rigorously, then decide what's worth shipping. For clinical briefs, a safety-focused structure that surfaces uncertainty is worth the verbosity cost.
