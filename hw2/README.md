# HW2: Clinical Brief Generator

Building and evaluating a generative AI workflow through prompt iteration.

## Problem

Clinicians in resource-constrained settings need concise, structured briefs of patient status during time-pressured encounters. The challenge is synthesizing multiple data sources (vitals, labs, history, medications) into actionable summaries that surface safety concerns and missing information.

## Solution

A clinical brief generator that takes raw patient context and produces structured summaries. The workflow tests three distinct prompt approaches to understand how prompt design affects output quality.

## Prompt Versions

**V1: Unstructured Narrative (Baseline)**
- Simple instruction to summarize
- Produces prose narratives
- Minimal structure guidance
- Fast, flexible, can miss key elements

**V2: Structured with Sections**
- Explicit format instructions (PRESENTATION, VITALS & LABS, MEDICATIONS, ASSESSMENT, NEXT STEPS)
- Organizes information into predictable sections
- Better for pattern matching, easier to parse
- May lose clinical nuance in rigid format

**V3: Safety-First (Production)**
- Prioritizes uncertainty and missing data
- Explicit clinician review boundaries
- Surfaces medication interactions and red flags
- Requires clinician involvement at every decision point

## Evaluation Methodology

Each brief is evaluated against five criteria:

- **has_vitals**: Does the brief include vital signs?
- **has_labs**: Are lab values mentioned?
- **has_assessment**: Is there a clinical impression?
- **has_action**: Are next steps clearly stated?
- **explicit_uncertainty**: Does the brief surface what is unknown?

Criteria are evaluated using simple keyword matching against the generated text. Results indicate whether each version covers the essential information categories.

## Test Cases

Three synthetic patient scenarios cover different complexity levels:

1. **Simple Hypertension**: Single problem, minimal data, straightforward case
2. **Complex Comorbidities**: Multiple diagnoses, polypharmacy, drug interaction risks
3. **Incomplete Data**: Missing information that requires clinician clarification

## Usage

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY="your_key_here"
python3 brief_generator.py
```

Output is saved to `outputs/evaluation_results.json`.

## Key Findings

- **Unstructured prompts** produce readable prose but often omit critical information categories
- **Structured prompts** cover key sections reliably but can feel formulaic
- **Safety-focused prompts** properly surface uncertainty and clinician review requirements, supporting human oversight

V3 (Safety-First) is recommended for production because it maintains explicit human review boundaries and surfaces missing data that could affect patient safety.

## Limitations

- Synthetic test cases only
- Keyword-based evaluation is crude compared to clinical expert review
- No real patient data or integration with actual EHR systems
- Prompt design reflects healthcare context but applies general principles
- Model outputs can hallucinate clinical details if not constrained

This is an educational prototype demonstrating prompt iteration methodology. Any real clinical application would require expert validation and formal safety testing.
