# HW2 Prompt Iteration Log

A first-person narrative of how the three prompt versions evolved.

## Starting Point

I started with the simplest possible prompt: "summarize this patient." I wanted a baseline to measure improvement against. Anything I added later had to justify itself by outperforming this baseline.

## V1: Unstructured Narrative

```
SYSTEM: You are a clinical documentation assistant. Summarize patient context for a clinician.
USER: Write a brief narrative summary of this patient's clinical status: {context}
```

### What happened
V1 produced readable prose. For Case 1 (simple hypertension) it gave a one-paragraph summary that any non-clinician could understand. The keyword evaluator scored 2-3 out of 5 on most cases.

### What broke
- Output structure varied wildly between cases. Some had clear sections, others were dense paragraphs.
- The LLM-as-judge rated V1 at 3.40/10 average. Specifically: structure (often 0), uncertainty handling (always 0), safety posture (always 0).
- For Case 3 (incomplete data), V1 noticed pending tests but didn't escalate. It just narrated the situation.
- For Case 4 (pediatric escalation), V1 recognized severity but didn't trigger any explicit clinician review boundary.

### Lesson
Free-form prompts produce variable structure. Even when the LLM has the right clinical instincts, the format makes it hard to scan in 30 seconds, and there's nothing forcing the model to flag what it doesn't know.

## V2: Structured with Explicit Sections

```
SYSTEM: You are a clinical documentation assistant. Produce structured summaries with consistent sections. Be concise.
USER: Write a clinical brief using this exact format:
  PRESENTATION: [...]
  VITALS & LABS: [...]
  MEDICATIONS: [...]
  ASSESSMENT: [...]
  NEXT STEPS: [...]
  Patient context: {context}
```

### What happened
V2 jumped to 7.20/10 average. The format constraint was doing real work: every brief now had ASSESSMENT and NEXT STEPS sections explicitly, which clinicians can scan.

### What still broke
- Uncertainty handling stayed at 0 for most cases. The format had no slot for "what's missing" so the model rarely surfaced it.
- Safety posture only scored 1 occasionally. V2 didn't have any instruction to defer to clinician judgment, so it would produce confident-sounding assessments.
- For Case 3 (incomplete data), V2 listed pending tests in VITALS but didn't make missing data a first-class concern.

### Lesson
Structure improves consistency and scannability. It does not, by itself, change what the model thinks is important. If the prompt doesn't ask for missing data, the model fills the section it's given.

## V3: Few-shot + Chain-of-Thought + Safety-First

```
SYSTEM: You are a clinical safety assistant. Your job is to surface uncertainties, missing data, and medication interactions that require clinician review.
  You work in resource-constrained settings where clinicians see 40+ patients per shift.
  Your briefs must be auditable.

USER: [Two complete worked examples showing REASONING then OUTPUT in the target format]
  Now produce a brief for the following case. First write your step-by-step REASONING (3-5 bullets), then the OUTPUT.
  INPUT: {context}
```

### Three changes from V2

1. **Role reframing**: from "documentation assistant" to "safety assistant." The job is no longer to summarize, it's to surface what could go wrong.

2. **Few-shot examples** (Brown et al., 2020): two complete reasoning + output pairs. The examples show the model what "good" looks like, including the missing-data discipline and the explicit clinician review boundary.

3. **Chain-of-thought scaffolding** (Wei et al., 2023): explicit "REASONING" section before the OUTPUT forces intermediate reasoning. The reasoning step catches things the model would otherwise skip.

### What happened
V3 jumped to 9.80/10 average. The LLM-as-judge gave 10/10 on four of five cases. The one case that scored 9 (Case 5, healthy patient) lost a point on actionability because there isn't much to do for a healthy person, which is the right behavior.

### Specific wins
- Case 3 (incomplete data): V3 flagged "CRITICAL" missing data including pregnancy test (which V1 and V2 both missed entirely)
- Case 4 (pediatric escalation): V3 named Kawasaki disease and explicit time-sensitivity (IVIG before day 10)
- Case 2 (complex): V3 correctly framed the new chest tightness as "unstable angina until proven otherwise" rather than reassuring narrative

### Why it worked
- Few-shot examples acted as in-context training. The model saw "MISSING DATA: lipid panel, urine ACR..." in the examples and produced similar lists for new cases.
- The CoT REASONING step caught the right clinical concerns before the model committed to an output.
- The "safety assistant" frame oriented the model toward escalation rather than reassurance.

## Cross-Cutting Observations

### Heuristic vs LLM-judge scores diverged
The keyword-based heuristic ranked V2 ahead of V3 on three of five cases because V2 had the literal word "ASSESSMENT" in its output and V3 used "CLINICIAN REVIEW REQUIRED" instead. The heuristic was matching surface patterns, not semantic quality. The LLM-judge inverted this ranking because it evaluated the actual clinical content.

This is exactly the kind of evaluation mismatch the course material warns about. Heuristic eval gives fast feedback but biases toward what it can measure, not what matters.

### Few-shot is more powerful than structure constraints
V2 (structure) gave a +3.8 point improvement over V1.
V3 (structure + few-shot + CoT) gave another +2.6 points over V2.
The marginal improvement from V2 to V3 came from showing the model what good reasoning looks like, not from adding more format constraints.

### Safety posture is a prompt design choice, not a model property
V1 and V2 produced confident-sounding briefs. V3 explicitly required clinician review even on healthy patients. The model didn't suddenly become more cautious. The prompt asked it to be cautious, and it complied.

## What I Would Do Next

1. **Adversarial cases**: add cases where the input contains plausible-looking but wrong data (e.g., a documented allergy that contradicts a prescribed medication). Test whether V3 catches the inconsistency.

2. **Multi-judge eval**: use 2-3 different judge models and check inter-rater agreement. A single judge can be biased.

3. **Clinician validation**: have a real physician score 5 random briefs blinded. Compare to the LLM-judge scores to validate the rubric.

4. **Production guardrails**: V3's "CLINICIAN REVIEW REQUIRED: Yes" appears on every case. In production, fatigue would set in. Need a hierarchy of urgency that maps to actual clinical workflow.

5. **Cost analysis**: V3 prompts are ~6x longer than V1 due to few-shot examples. Production economics depend on whether the quality gain justifies the token cost.

## Course Material Tie-In

- Brown et al., 2020 (Few-shot Learners): V3's two-example structure is the standard few-shot pattern. The improvement over V2 confirms the paper's finding that in-context examples shape output meaningfully.
- Wei et al., 2023 (Chain-of-Thought): V3's explicit REASONING step before OUTPUT is the CoT pattern. The improvement confirms that requesting intermediate reasoning improves final-answer quality on multi-step problems.
- Challapally et al., 2025 (GenAI Divide): the GenAI Divide paper notes that 95% of enterprise pilots fail to deliver ROI because they're built without rigorous evaluation. The V1 vs V3 comparison shows why: shipping V1 would have looked fine on demos and quietly underperformed in real use.
