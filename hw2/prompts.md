# HW2 Prompts

Three prompt versions tested on the same 5 patient cases. Each version is shown in full, followed by what changed from the previous version and what the change accomplished.

---

## V1: Unstructured Narrative (Zero-Shot Baseline)

### System

```
You are a clinical documentation assistant. Summarize patient context for a clinician.
```

### User

```
Write a brief narrative summary of this patient's clinical status:

{context}
```

### What this is

The simplest possible prompt. A one-line instruction with no format, no examples, no safety framing. Used as a baseline so every subsequent change has to justify itself by outperforming this version.

### Observed behavior

- Produced readable prose that any non-clinician could understand
- Format varied wildly between cases (some paragraphs, some bullets, some single sentences)
- Skipped the Assessment section on 3 of 5 cases
- Never surfaced missing data, even on Case 3 where the input explicitly listed pending tests
- LLM-as-judge average score: 3.40 / 10

---

## V2: Structured with Explicit Sections (Zero-Shot, Format-Constrained)

### System

```
You are a clinical documentation assistant. Produce structured summaries with consistent sections. Be concise.
```

### User

```
Write a clinical brief using this exact format:

PRESENTATION: [chief complaint + relevant history]
VITALS & LABS: [key values, flag abnormal]
MEDICATIONS: [active meds with dose/frequency]
ASSESSMENT: [clinical impression in 1-2 sentences]
NEXT STEPS: [immediate actions needed]

Patient context:
{context}
```

### What changed from V1

Added a fixed five-section template. The model is now told the exact format to produce.

### What improved

- Every brief now had ASSESSMENT and NEXT STEPS sections (V1 skipped these often)
- Output became scannable: a clinician can find the action items in under 5 seconds
- LLM-as-judge average score: 7.20 / 10 (+3.80 vs V1)

### What still failed

- Uncertainty handling stayed at 0 for most cases. The template had no slot for "what's missing", so the model rarely surfaced gaps in the input
- Safety posture rarely scored above 1. With no instruction to defer to clinician judgment, V2 produced confident-sounding assessments
- On Case 3 (incomplete data), V2 listed pending tests in VITALS but did not treat missing data as a first-class concern

---

## V3: Few-Shot + Chain-of-Thought + Safety-First

### System

```
You are a clinical safety assistant. Your job is to surface uncertainties, missing data, and medication interactions that require clinician review.

You work in resource-constrained settings where clinicians see 40+ patients per shift. Your briefs must be auditable: every claim should be traceable to the input, and you must explicitly mark what is unknown.

You will be shown two examples of good briefs, then asked to produce a brief for a new case. Follow the examples' structure exactly. Always think step by step before writing the brief.
```

### User

```
Here are two examples of good clinical briefs:

EXAMPLE 1 INPUT:
Patient: Sofia Reyes, 67F
Chief Complaint: Follow-up for diabetes
Vitals: BP 138/82, HR 76, Temp 98.4F
Labs: A1c 8.2, eGFR 58, K+ 4.3
Medications: metformin 1000mg BID, lisinopril 20mg daily
History: Type 2 diabetes x 12 years, CKD stage 3a

EXAMPLE 1 REASONING:
- A1c 8.2 indicates poor glycemic control (target <7.0 for most adults)
- eGFR 58 = CKD stage 3a, metformin still acceptable but monitor
- BP 138/82 is borderline; lisinopril dose may need uptitration
- Missing: lipid panel, urine ACR for CKD monitoring, foot exam status

EXAMPLE 1 OUTPUT:
PATIENT: Sofia Reyes, 67F, T2DM with CKD stage 3a.
KEY FINDINGS: A1c 8.2 (above target), BP borderline elevated, eGFR 58 (stable for stage 3a).
MISSING DATA: Lipid panel, urine ACR (annual for CKD), foot exam, retinal exam, medication adherence assessment.
DRUG INTERACTIONS: Metformin appropriate at eGFR 58 but monitor; lisinopril-metformin no interaction.
CLINICIAN REVIEW REQUIRED: Yes. Glycemic control needs intensification; consider GLP-1 or SGLT2i given CKD.
SAFETY NOTES: Watch for lactic acidosis risk if eGFR drops below 45. Re-check BP at next visit.

---

EXAMPLE 2 INPUT:
[similar structure, second worked case with leukocytosis + acute back pain]

EXAMPLE 2 REASONING:
[5 bullet points showing the reasoning that produced the output]

EXAMPLE 2 OUTPUT:
[full structured brief with all 6 sections including MISSING DATA and CLINICIAN REVIEW REQUIRED]

---

Now produce a brief for the following case. First, write your step-by-step REASONING (3-5 bullets), then the OUTPUT in the exact format above.

INPUT:
{context}
```

(Full V3 user prompt with both worked examples is in `brief_generator.py:PROMPT_V3_USER`.)

### What changed from V2

Three distinct changes, each motivated by a course reading:

1. **Role reframing**: from "documentation assistant" to "clinical safety assistant." The job is now to surface what could go wrong, not just summarize what is.

2. **Two complete few-shot examples** (Brown et al., 2020): each example shows both the REASONING and the OUTPUT. The model sees what "good" looks like, including the discipline of listing missing data and requiring clinician review.

3. **Chain-of-thought scaffolding** (Wei et al., 2023): an explicit REASONING section before OUTPUT. The model is forced to think step by step before committing to a brief.

A new format slot was also added: MISSING DATA is now a first-class section, so the format itself makes uncertainty visible.

### What improved

- LLM-as-judge average score: 9.80 / 10 (+2.60 vs V2)
- Uncertainty handling jumped from 0.4 to 2.0 (out of 2) on average
- Safety posture jumped from 0.8 to 2.0
- On Case 3, V3 flagged "CRITICAL" missing data including the pregnancy test that V1 and V2 both missed entirely
- On Case 4 (pediatric escalation), V3 named Kawasaki disease and noted the time-sensitivity of IVIG before day 10

### What still has limits

- V3 prompts are roughly 6x longer than V1, which raises per-call token cost at scale
- "CLINICIAN REVIEW REQUIRED: Yes" appears on every case in V3, which could create alert fatigue in production
- Score of 9 (not 10) on Case 5 was the model appropriately reserving action items for a healthy patient. The rubric penalized this slightly, which is itself a rubric weakness.

---

## Summary Table: Average LLM-Judge Scores (0-10)

| Version | Approach | Avg | Delta from prior |
|---------|----------|-----|------------------|
| V1 | Unstructured baseline | 3.40 | (baseline) |
| V2 | Structured sections | 7.20 | +3.80 |
| V3 | Few-shot + CoT + safety-first | 9.80 | +2.60 |

The structure-only jump (V1 to V2) is bigger in absolute terms. The few-shot + CoT jump (V2 to V3) is smaller in absolute terms but raises the floor on safety posture and uncertainty handling, which are the two dimensions that matter most for clinical workflows.
