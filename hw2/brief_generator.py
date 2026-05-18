#!/usr/bin/env python3
"""HW2 Clinical Brief Generator with prompt iteration and evaluation.

Three prompt versions demonstrate the progression from naive to production-ready:
- V1: Unstructured baseline (zero-shot, no structure guidance)
- V2: Structured sections (zero-shot, format constraints)
- V3: Few-shot + Chain-of-Thought + safety-first (production candidate)

Backends:
- ollama: real LLM calls to local Ollama server (default if available)
- mock: pre-recorded outputs for offline grading (--mock flag)
"""

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()


DEFAULT_OLLAMA_URL = "http://localhost:11434/v1"
DEFAULT_MODEL = "devstral:latest"


PROMPT_V1_SYSTEM = (
    "You are a clinical documentation assistant. Summarize patient context for a clinician."
)
PROMPT_V1_USER = "Write a brief narrative summary of this patient's clinical status:\n\n{context}"


PROMPT_V2_SYSTEM = (
    "You are a clinical documentation assistant. Produce structured summaries "
    "with consistent sections. Be concise."
)
PROMPT_V2_USER = """Write a clinical brief using this exact format:

PRESENTATION: [chief complaint + relevant history]
VITALS & LABS: [key values, flag abnormal]
MEDICATIONS: [active meds with dose/frequency]
ASSESSMENT: [clinical impression in 1-2 sentences]
NEXT STEPS: [immediate actions needed]

Patient context:
{context}"""


PROMPT_V3_SYSTEM = """You are a clinical safety assistant. Your job is to surface uncertainties, missing data, and medication interactions that require clinician review.

You work in resource-constrained settings where clinicians see 40+ patients per shift. Your briefs must be auditable: every claim should be traceable to the input, and you must explicitly mark what is unknown.

You will be shown two examples of good briefs, then asked to produce a brief for a new case. Follow the examples' structure exactly. Always think step by step before writing the brief."""

PROMPT_V3_USER = """Here are two examples of good clinical briefs:

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
Patient: Lucas Oliveira, 42M
Chief Complaint: Acute lower back pain, no trauma
Vitals: BP 122/78, HR 88, Temp 99.1F
Labs: WBC 11.2, ESR pending
Medications: ibuprofen 400mg PRN (self-medicating x 3 days)
History: Office worker, no prior back issues

EXAMPLE 2 REASONING:
- Acute back pain without trauma + low-grade fever + elevated WBC raises red flag
- Must rule out: discitis, epidural abscess, kidney pathology
- ESR pending will help triage but should not delay imaging if neurological symptoms
- Missing: neurological exam, urinalysis, imaging, IV drug use history

EXAMPLE 2 OUTPUT:
PATIENT: Lucas Oliveira, 42M, acute atraumatic back pain with concerning features.
KEY FINDINGS: Low-grade fever, leukocytosis (WBC 11.2), self-medicating with NSAIDs x 3 days.
MISSING DATA: Neurological exam (sensation, reflexes, saddle anesthesia), urinalysis, imaging, IV drug use history, immunocompromise status.
DRUG INTERACTIONS: NSAID use masking fever; renal risk if dehydrated.
CLINICIAN REVIEW REQUIRED: Yes, URGENT. Red flags present (fever + acute back pain + leukocytosis) require workup for spinal infection.
SAFETY NOTES: Do not delay imaging if any neurological deficit. Hold further NSAIDs until renal function checked.

---

Now produce a brief for the following case. First, write your step-by-step REASONING (3-5 bullets), then the OUTPUT in the exact format above.

INPUT:
{context}"""


@dataclass
class PromptVersion:
    """A prompt configuration."""

    id: str
    name: str
    system: str
    user_template: str


PROMPTS = [
    PromptVersion(
        id="v1_unstructured",
        name="V1 Unstructured (zero-shot)",
        system=PROMPT_V1_SYSTEM,
        user_template=PROMPT_V1_USER,
    ),
    PromptVersion(
        id="v2_structured",
        name="V2 Structured (zero-shot, format constrained)",
        system=PROMPT_V2_SYSTEM,
        user_template=PROMPT_V2_USER,
    ),
    PromptVersion(
        id="v3_fewshot_cot",
        name="V3 Few-shot + CoT + Safety-first",
        system=PROMPT_V3_SYSTEM,
        user_template=PROMPT_V3_USER,
    ),
]


TEST_CASES = [
    {
        "id": "case_1_simple",
        "name": "Simple hypertension (normal)",
        "complexity": "normal",
        "context": """Patient: Maria Santos, 55-year-old female
Chief Complaint: Hypertension screening visit
Vitals: BP 158/94, HR 72, RR 16, Temp 98.6F
Labs: K+ 4.1, Cr 0.9, eGFR 78
Current Medications: None
History: No prior cardiology, nonsmoker, sedentary""",
    },
    {
        "id": "case_2_complex",
        "name": "Multiple comorbidities (complex)",
        "complexity": "complex",
        "context": """Patient: João Silva, 72-year-old male
Chief Complaint: Routine follow-up, chest tightness with exertion
Vitals: BP 142/88, HR 68, RR 18, Temp 98.4F
Labs: K+ 3.9, Cr 1.4, eGFR 45, TnI <0.01, Hgb 11.2
Current Medications: metoprolol 50mg daily, lisinopril 10mg daily, atorvastatin 40mg daily, aspirin 81mg daily
History: Type 2 diabetes, prior MI (2018), CKD stage 3b, smoker (15 cigs/day)
Recent: Stress test 6mo ago normal, no change in symptoms since then""",
    },
    {
        "id": "case_3_incomplete",
        "name": "Incomplete data (ambiguous)",
        "complexity": "ambiguous",
        "context": """Patient: Ana Cardoso, 38-year-old female
Chief Complaint: Dyspnea on exertion x 1 week
Vitals: BP 118/76, HR 92, RR 22, Temp 99.2F
Labs: WBC 12.1 [pending CXR, D-dimer not ordered]
Current Medications: OCPs (dose unknown), antihistamine PRN
History: No prior cardiac disease, patient reports "usual allergies"
Recent: Returned from trip to rural area 10 days ago, denies travel pneumonia exposure""",
    },
    {
        "id": "case_4_edge_pediatric",
        "name": "Pediatric escalation (edge case)",
        "complexity": "edge",
        "context": """Patient: Pedro Almeida, 4-year-old male
Chief Complaint: Fever x 5 days, refusing oral intake
Vitals: BP 92/58, HR 138, RR 32, Temp 39.8C, SpO2 94% RA
Labs: WBC 18.4, CRP 142, no cultures drawn yet
Current Medications: Acetaminophen 250mg q6h (mother giving since day 1)
History: Up to date on vaccinations, no chronic conditions
Recent: Sibling had similar symptoms 1 week ago, resolved spontaneously""",
    },
    {
        "id": "case_5_no_flags",
        "name": "No-flag control (healthy)",
        "complexity": "control",
        "context": """Patient: Carlos Mendes, 32-year-old male
Chief Complaint: Annual physical, no complaints
Vitals: BP 118/74, HR 64, RR 14, Temp 98.4F
Labs: CBC normal, BMP normal, lipid panel WNL, A1c 5.2
Current Medications: None
History: No medical conditions, regular exercise 4x/week, nonsmoker, occasional alcohol
Recent: All age-appropriate screenings up to date""",
    },
]


MOCK_OUTPUTS: dict[str, dict[str, str]] = {
    "v1_unstructured": {
        "case_1_simple": "Maria Santos is a 55-year-old woman with elevated blood pressure (158/94) on screening visit. Heart rate and respiratory rate are normal. Renal function and potassium are within normal limits. She is currently not on any antihypertensive therapy and has no prior cardiology history. She is a nonsmoker and reports a sedentary lifestyle. Initial management should focus on lifestyle modification including dietary changes and increased physical activity, with follow-up to assess if pharmacotherapy is needed.",
        "case_2_complex": "João Silva is a 72-year-old man with extensive cardiac history presenting for routine follow-up with new exertional chest tightness. He has a prior myocardial infarction (2018), type 2 diabetes, CKD stage 3b, and active smoking. His vitals are stable with borderline hypertension and bradycardia (likely beta-blocker effect). Troponin is negative, hemoglobin shows mild anemia. He is on appropriate post-MI medications. His recent stress test was normal but his symptoms have not changed since then. Smoking cessation should be addressed.",
        "case_3_incomplete": "Ana Cardoso is a 38-year-old woman with one week of exertional dyspnea. She has tachypnea and a low-grade fever. White blood cell count is mildly elevated. Chest X-ray is pending and D-dimer was not ordered. She returned from a rural area 10 days ago. She takes OCPs but the dose is unknown. The clinical picture is concerning for either respiratory infection or possibly pulmonary embolism given the OCP use. Additional workup is needed before management decisions can be made.",
        "case_4_edge_pediatric": "Pedro Almeida is a 4-year-old boy with 5 days of fever and poor oral intake. He has high fever, tachycardia, tachypnea, and mildly low oxygen saturation. His WBC and CRP are significantly elevated suggesting bacterial infection. He has been receiving acetaminophen at home. He is up to date on vaccinations. His sibling had similar symptoms that resolved spontaneously. This presentation requires urgent evaluation given the prolonged fever, elevated inflammatory markers, and signs of dehydration.",
        "case_5_no_flags": "Carlos Mendes is a 32-year-old man presenting for his annual physical with no specific complaints. All vital signs are within normal limits. His complete blood count, basic metabolic panel, lipid panel, and hemoglobin A1c are all normal. He takes no medications and has no chronic medical conditions. He maintains a healthy lifestyle with regular exercise and no smoking. All age-appropriate screenings are current. He should continue his current lifestyle and return for his next annual visit.",
    },
    "v2_structured": {
        "case_1_simple": "PRESENTATION: 55-year-old female with hypertension screening. No prior cardiac history.\nVITALS & LABS: BP 158/94 (elevated, Stage 2), HR 72, RR 16, K+ 4.1 (normal), Cr 0.9 (normal), eGFR 78 (normal)\nMEDICATIONS: None currently\nASSESSMENT: Stage 2 hypertension without evidence of end-organ damage. No acute symptoms.\nNEXT STEPS: Lifestyle modification counseling, repeat BP measurement in 1 month, consider pharmacotherapy if persistent above 140/90.",
        "case_2_complex": "PRESENTATION: 72-year-old male with new exertional chest tightness on routine follow-up. Significant history of MI (2018), diabetes, CKD stage 3b, active smoker.\nVITALS & LABS: BP 142/88, HR 68, TnI <0.01 (negative), Hgb 11.2 (mild anemia), eGFR 45 (reduced)\nMEDICATIONS: Metoprolol 50mg daily, lisinopril 10mg daily, atorvastatin 40mg daily, aspirin 81mg daily (appropriate post-MI regimen)\nASSESSMENT: New stable angina in high-risk patient. Negative troponin reassuring acutely. Mild anemia may worsen ischemia.\nNEXT STEPS: Cardiology consult urgently, smoking cessation intervention, repeat stress test or coronary angiography, workup anemia etiology.",
        "case_3_incomplete": "PRESENTATION: 38-year-old female with one week of exertional dyspnea. Recent travel to rural area, OCP use.\nVITALS & LABS: RR 22 (tachypneic), Temp 99.2F (low-grade fever), WBC 12.1 (elevated). CXR pending, D-dimer not ordered.\nMEDICATIONS: OCPs (dose unknown), antihistamine PRN\nASSESSMENT: Differential includes pulmonary embolism (given OCP use), community-acquired pneumonia, atypical infection from travel.\nNEXT STEPS: STAT chest imaging, D-dimer or CT-PE protocol given OCP use, blood cultures if infectious workup pursued, full medication reconciliation.",
        "case_4_edge_pediatric": "PRESENTATION: 4-year-old male with 5 days of fever and poor oral intake. Sibling had similar resolved illness.\nVITALS & LABS: Temp 39.8C, HR 138 (tachycardic), RR 32 (tachypneic), SpO2 94% (mildly hypoxic), WBC 18.4 (elevated), CRP 142 (markedly elevated)\nMEDICATIONS: Acetaminophen 250mg q6h\nASSESSMENT: Prolonged febrile illness with elevated inflammatory markers and signs of dehydration. Differential includes bacterial infection, Kawasaki disease (given duration), or atypical presentation.\nNEXT STEPS: IV fluid resuscitation, blood and urine cultures, consider lumbar puncture, pediatric infectious disease consultation, hospital admission for monitoring.",
        "case_5_no_flags": "PRESENTATION: 32-year-old male for annual physical, asymptomatic.\nVITALS & LABS: BP 118/74, HR 64, RR 14, all normal. CBC, BMP, lipid panel, A1c 5.2 all normal.\nMEDICATIONS: None\nASSESSMENT: Healthy adult male with no concerning findings. All screening labs normal.\nNEXT STEPS: Continue current healthy lifestyle. Return in 12 months for next annual exam. Maintain age-appropriate screening schedule.",
    },
    "v3_fewshot_cot": {
        "case_1_simple": """REASONING:
- BP 158/94 meets Stage 2 hypertension criteria; isolated finding without symptoms
- Normal renal function and electrolytes; no acute end-organ damage signals
- No prior history but sedentary lifestyle is a modifiable risk factor
- Missing: lipid panel, glucose, EKG, family history, secondary causes workup

OUTPUT:
PATIENT: Maria Santos, 55F with newly identified Stage 2 hypertension.
KEY FINDINGS: BP 158/94 (Stage 2), normal renal function, no current medications, sedentary lifestyle.
MISSING DATA: Lipid panel, fasting glucose, EKG, family history of premature CAD, urine albumin-creatinine ratio, baseline secondary hypertension workup.
DRUG INTERACTIONS: None identified (no current medications).
CLINICIAN REVIEW REQUIRED: Yes. Stage 2 BP usually warrants pharmacologic therapy alongside lifestyle change; clinician should also consider secondary causes given new presentation in middle-aged woman.
SAFETY NOTES: Single BP reading may not represent average; confirm with home or ambulatory monitoring before committing to lifelong therapy. Screen for orthostatic symptoms before initiating treatment.""",
        "case_2_complex": """REASONING:
- New exertional chest tightness in patient with prior MI is unstable angina until proven otherwise
- Negative single troponin does not rule out unstable angina, only acute MI
- eGFR 45 (CKD stage 3b) constrains medication choices and contrast use
- Anemia (Hgb 11.2) worsens myocardial oxygen supply
- Active smoking is the highest-impact modifiable risk factor

OUTPUT:
PATIENT: João Silva, 72M with prior MI, presenting with new exertional chest tightness.
KEY FINDINGS: New angina symptoms in high-risk patient, negative single troponin, CKD stage 3b limits contrast options, mild anemia, active smoker.
MISSING DATA: Repeat troponin (serial), full ECG with comparison to baseline, ejection fraction, smoking pack-year history, medication adherence, anemia workup (iron studies, B12, folate).
DRUG INTERACTIONS: Current regimen is appropriate post-MI. CKD stage 3b limits future options (avoid NSAIDs, dose-adjust metformin if added).
CLINICIAN REVIEW REQUIRED: Yes, URGENT. Unstable angina pattern needs cardiology evaluation today, not deferred to outpatient.
SAFETY NOTES: Do not perform stress test without cardiology input given symptom pattern. If invasive workup needed, hydrate aggressively pre-contrast given CKD. Smoking cessation is highest-yield intervention but secondary to acute evaluation.""",
        "case_3_incomplete": """REASONING:
- One week of progressive dyspnea on exertion in 38F on OCPs is suspicious for pulmonary embolism
- Tachypnea and low-grade fever overlap PE, pneumonia, and acute viral illness presentations
- D-dimer was NOT ordered despite classic risk-stratification need
- Travel history adds infectious differential (community-acquired pneumonia, atypical pathogens)
- Pregnancy status is critical and not documented

OUTPUT:
PATIENT: Ana Cardoso, 38F with one week exertional dyspnea, OCP use, recent travel.
KEY FINDINGS: Tachypnea (RR 22), low-grade fever, leukocytosis (WBC 12.1), risk factors for both PE (OCP) and infection (travel).
MISSING DATA: CRITICAL - D-dimer not ordered, CXR pending (no result), pregnancy test not documented, full medication reconciliation (OCP dose unknown, possibly other agents), neurological exam, oxygen saturation, lower extremity exam for DVT signs.
DRUG INTERACTIONS: Cannot fully assess without complete medication list. OCP use increases VTE risk independent of other factors.
CLINICIAN REVIEW REQUIRED: Yes, URGENT. Workup is incomplete for two life-threatening differentials (PE, pneumonia) that require different treatments.
SAFETY NOTES: Empiric anticoagulation should not start without pregnancy test and risk-stratified imaging. Wells score and PERC rule should be applied. Do not discharge until PE is reasonably excluded or treated.""",
        "case_4_edge_pediatric": """REASONING:
- 5 days of fever in a 4-year-old is at threshold for Kawasaki disease evaluation
- Tachycardia (HR 138) and tachypnea (RR 32) may indicate sepsis or dehydration
- SpO2 94% in a child is concerning for early respiratory compromise
- WBC 18.4 and CRP 142 strongly suggest bacterial process or hyperinflammatory state
- Sibling history may be coincidental viral or relevant exposure

OUTPUT:
PATIENT: Pedro Almeida, 4M with 5 days fever, refusing PO, dehydration signs, marked inflammation.
KEY FINDINGS: Prolonged fever, tachycardia, tachypnea, borderline hypoxia, leukocytosis, elevated CRP, dehydration signs (refusing oral intake).
MISSING DATA: Blood and urine cultures (none drawn), lumbar puncture decision, hydration status (cap refill, mucous membranes), Kawasaki criteria assessment (rash, conjunctivitis, lymphadenopathy, oral changes, extremity changes), urinalysis, viral PCR panel, sibling's actual diagnosis.
DRUG INTERACTIONS: Acetaminophen dose appears appropriate for age/weight assumed; verify weight-based dose.
CLINICIAN REVIEW REQUIRED: Yes, URGENT. This child needs hospital evaluation today with pediatric specialist; do not manage as outpatient.
SAFETY NOTES: Sepsis must be excluded before any non-urgent workup. Fluid resuscitation may be needed before cultures if shock signs develop. Kawasaki disease is time-sensitive (IVIG before day 10).""",
        "case_5_no_flags": """REASONING:
- All vitals within normal limits in a 32-year-old man
- Complete metabolic panel, CBC, lipids, A1c all normal
- No current medications and no chronic conditions
- Lifestyle factors all favorable (exercise, nonsmoker, moderate alcohol)
- Screenings are current

OUTPUT:
PATIENT: Carlos Mendes, 32M, healthy adult for annual physical.
KEY FINDINGS: Normal vitals, normal CBC/BMP/lipids/A1c, asymptomatic, age-appropriate screenings current.
MISSING DATA: Family history of early CAD or cancer (relevant for risk stratification at this age), mental health screening (PHQ-2/GAD-2), sexual health screening, dental/vision exam dates, sleep quality assessment.
DRUG INTERACTIONS: None (no medications).
CLINICIAN REVIEW REQUIRED: No urgent flags. Routine reinforcement of healthy behaviors appropriate.
SAFETY NOTES: Even in healthy patients, document mental health and family history to catch hereditary risks early. Continue annual visits; no labs needed sooner unless symptoms develop.""",
    },
}


def call_llm(version: PromptVersion, context: str, model: str, base_url: str) -> str:
    """Make a real LLM call using OpenAI-compatible API."""
    from openai import OpenAI

    client = OpenAI(base_url=base_url, api_key=os.getenv("LLM_API_KEY", "ollama"))
    user_prompt = version.user_template.format(context=context)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": version.system},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=800,
        temperature=0.2,
    )
    return response.choices[0].message.content or ""


def get_mock(version_id: str, case_id: str) -> str:
    """Return pre-recorded mock output."""
    return MOCK_OUTPUTS.get(version_id, {}).get(case_id, "[mock output unavailable]")


def generate_brief(
    version: PromptVersion,
    case: dict[str, Any],
    mock: bool,
    model: str,
    base_url: str,
) -> str:
    """Generate a brief for the given case using the given prompt version."""
    if mock:
        return get_mock(version.id, case["id"])
    return call_llm(version, case["context"], model, base_url)


def evaluate_brief(brief: str) -> dict[str, bool]:
    """Heuristic evaluation: keyword presence across 5 criteria."""
    text = brief.lower()
    return {
        "has_vitals": any(kw in text for kw in ["bp", "hr ", "heart rate", "temp"]),
        "has_labs": any(kw in text for kw in ["labs", "k+", "wbc", "hgb", "egfr", "cr "]),
        "has_assessment": any(kw in text for kw in ["assessment", "impression", "diagnosis"]),
        "has_action": any(kw in text for kw in ["next step", "recommend", "follow", "review", "consult"]),
        "explicit_uncertainty": any(kw in text for kw in ["missing", "unknown", "pending", "not documented", "not ordered"]),
    }


def heuristic_score(eval_dict: dict[str, bool]) -> int:
    """Sum of true criteria, 0-5."""
    return sum(1 for v in eval_dict.values() if v)


def detect_backend(mock_flag: bool, base_url: str) -> tuple[str, str]:
    """Decide which backend to use based on flags and availability.

    Returns (mode, message).
    """
    if mock_flag:
        return ("mock", "Forced mock mode via --mock flag.")

    import urllib.request
    import urllib.error

    try:
        urllib.request.urlopen(base_url.replace("/v1", "/api/tags"), timeout=2)
        return ("live", f"Live mode: Ollama detected at {base_url}.")
    except (urllib.error.URLError, OSError):
        return ("mock", f"No Ollama server at {base_url}; falling back to mock mode.")


def main():
    parser = argparse.ArgumentParser(description="Clinical brief generator with prompt iteration.")
    parser.add_argument("--mock", action="store_true", help="Force mock mode (no LLM call)")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Ollama model name")
    parser.add_argument("--base-url", default=DEFAULT_OLLAMA_URL, help="OpenAI-compatible base URL")
    parser.add_argument("--case", help="Run only this case ID")
    parser.add_argument("--version", help="Run only this prompt version ID")
    args = parser.parse_args()

    mode, msg = detect_backend(args.mock, args.base_url)
    print(f"[mode] {msg}")
    if mode == "live":
        print(f"[model] {args.model}")
    print()

    test_cases = [c for c in TEST_CASES if not args.case or c["id"] == args.case]
    prompt_versions = [p for p in PROMPTS if not args.version or p.id == args.version]

    output_dir = Path(__file__).parent / "outputs"
    output_dir.mkdir(exist_ok=True)

    all_results = {
        "metadata": {
            "course": "BU.330.760.41 - Generative AI in Business",
            "assignment": "HW2 - Build and Evaluate Simple GenAI Workflow",
            "mode": mode,
            "model": args.model if mode == "live" else "mock",
            "test_case_count": len(test_cases),
            "prompt_version_count": len(prompt_versions),
        },
        "results": [],
    }

    for case in test_cases:
        print(f"=== Case: {case['name']} ({case['complexity']}) ===")
        case_record = {
            "case_id": case["id"],
            "case_name": case["name"],
            "complexity": case["complexity"],
            "context": case["context"],
            "briefs": [],
        }

        for version in prompt_versions:
            print(f"  [{version.name}] generating...")
            try:
                brief = generate_brief(version, case, mode == "mock", args.model, args.base_url)
            except Exception as e:
                print(f"    ERROR: {e}")
                brief = f"[ERROR: {e}]"

            eval_result = evaluate_brief(brief)
            score = heuristic_score(eval_result)
            print(f"    heuristic score: {score}/5")

            case_record["briefs"].append({
                "version_id": version.id,
                "version_name": version.name,
                "output": brief,
                "heuristic_eval": eval_result,
                "heuristic_score": score,
            })

        all_results["results"].append(case_record)
        print()

    output_file = output_dir / "generation_results.json"
    with open(output_file, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"Results saved to {output_file}")

    print_summary(all_results)


def print_summary(results: dict[str, Any]):
    """Print a compact summary table."""
    print("\n" + "=" * 70)
    print("HEURISTIC EVALUATION SUMMARY")
    print("=" * 70)
    print(f"{'Case':<35} {'V1':>6} {'V2':>6} {'V3':>6}")
    print("-" * 70)
    for case in results["results"]:
        row = f"{case['case_name'][:35]:<35}"
        scores = {b["version_id"]: b["heuristic_score"] for b in case["briefs"]}
        row += f" {scores.get('v1_unstructured', '-'):>6}"
        row += f" {scores.get('v2_structured', '-'):>6}"
        row += f" {scores.get('v3_fewshot_cot', '-'):>6}"
        print(row)


if __name__ == "__main__":
    main()
