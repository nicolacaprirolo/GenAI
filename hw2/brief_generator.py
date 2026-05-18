#!/usr/bin/env python3

import json
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()

MOCK_OUTPUTS = {
    "v1_unstructured": {
        "case_1_simple": "Maria Santos is a 55-year-old female with elevated blood pressure at 158/94 mmHg. Her heart rate is normal at 72 bpm. Labs show normal potassium (4.1) and renal function (creatinine 0.9, eGFR 78). She is not currently on any medications. Given her sedentary lifestyle and no prior heart disease history, initial hypertension management should focus on lifestyle modifications including salt reduction, weight loss if applicable, and increased physical activity. Follow-up monitoring needed to assess if medication is required.",
        "case_2_complex": "João Silva is a 72-year-old male presenting with chest tightness during exertion. He has significant comorbidities including type 2 diabetes, prior myocardial infarction (2018), and chronic kidney disease stage 3b (eGFR 45). Current medications include metoprolol, lisinopril, atorvastatin, and aspirin. He continues to smoke 15 cigarettes daily. Recent troponin is negative and prior stress testing was normal 6 months ago. His anemia (Hgb 11.2) warrants investigation. Critical concerns: ongoing smoking increases cardiac risk; medication regimen appears appropriate; requires cardiology evaluation for symptom change and smoking cessation counseling.",
        "case_3_incomplete": "Ana Cardoso is a 38-year-old female with acute dyspnea on exertion starting 1 week ago. Vitals show tachypnea (RR 22) and low-grade fever (99.2F). Labs show elevated WBC (12.1). Critical missing information: chest X-ray pending, D-dimer not ordered despite dyspnea. Recent travel to rural area 10 days ago raises concern for infectious or thromboembolic causes. Cannot exclude pulmonary embolism or pneumonia without additional imaging. Requires urgent chest imaging and consideration of anticoagulation workup. Current symptom severity and missing lab results make definitive assessment impossible.",
    },
    "v2_structured": {
        "case_1_simple": "PRESENTATION: 55-year-old female with hypertension screening. No prior cardiac history.\nVITALS & LABS: BP 158/94 (elevated), HR 72, RR 16, K+ 4.1 (normal), Cr 0.9 (normal), eGFR 78 (normal)\nMEDICATIONS: None currently\nASSESSMENT: Stage 1 hypertension without evidence of end-organ damage. No acute symptoms.\nNEXT STEPS: Lifestyle modification counseling, repeat BP monitoring in 1 month, consider pharmacotherapy if persistent elevation.",
        "case_2_complex": "PRESENTATION: 72-year-old male with chest tightness on exertion. History of MI (2018), diabetes, CKD stage 3b.\nVITALS & LABS: BP 142/88, HR 68, TnI <0.01 (negative), Hgb 11.2 (anemia), eGFR 45 (reduced clearance)\nMEDICATIONS: Metoprolol, lisinopril, atorvastatin, aspirin (appropriate for post-MI)\nASSESSMENT: Recurrent angina in high-risk patient. Negative troponin reassuring. Anemia may worsen ischemia.\nNEXT STEPS: Cardiology consult urgently, smoking cessation intervention, consider cardiac catheterization, investigate anemia cause.",
        "case_3_incomplete": "PRESENTATION: 38-year-old female with dyspnea on exertion x1 week. Recent travel to rural area.\nVITALS & LABS: RR 22 (tachypneic), Temp 99.2F (low fever), WBC 12.1 (elevated). CXR pending. D-dimer not ordered.\nMEDICATIONS: OCPs (dose unknown), antihistamine PRN\nASSESSMENT: Cannot complete without imaging. Differential includes PE, pneumonia, allergy/asthma.\nNEXT STEPS: STAT chest X-ray, consider D-dimer or CT-PE protocol, rule out venous thromboembolism, culture if infectious etiology suspected.",
    },
    "v3_safety_first": {
        "case_1_simple": "PATIENT: Maria Santos, 55F with hypertension screening.\nKEY FINDINGS: BP 158/94 (elevated), normal renal function, no medications, sedentary.\nMISSING DATA: Lipid panel, glucose, EKG, medication compliance history, family history of early CAD.\nDRUG INTERACTIONS: None identified (no current medications).\nCLINICIAN REVIEW REQUIRED: Yes. Elevated BP warrants assessment for secondary hypertension and end-organ damage before starting therapy.\nSAFETY NOTES: No acute warning signs, but target organ damage (left ventricular hypertrophy) possible with persistent elevation.",
        "case_2_complex": "PATIENT: João Silva, 72M with recurrent chest discomfort and extensive cardiac history.\nKEY FINDINGS: Chest pain with exertion, prior MI, CKD (eGFR 45), anemia, active smoking (high recurrence risk).\nMISSING DATA: Current chest pain severity, ECG changes, ejection fraction, complete medication adherence assessment.\nDRUG INTERACTIONS: Metoprolol + lisinopril + atorvastatin interactions assessed; aspirin appropriate. Smoking reduces drug efficacy.\nCLINICIAN REVIEW REQUIRED: Yes. Requires urgent cardiology evaluation. Anemia + ischemia + reduced renal clearance requires medication dosing review.\nSAFETY NOTES: High mortality risk. Smoking cessation is critical. ECG needed to assess acute ischemia.",
        "case_3_incomplete": "PATIENT: Ana Cardoso, 38F with acute dyspnea on exertion x1 week post travel.\nKEY FINDINGS: Tachypnea (RR 22), low fever, elevated WBC (12.1), recent travel exposure.\nMISSING DATA: CRITICAL - no CXR obtained, D-dimer not ordered, no EKG, exposure details unknown, medication details incomplete, pregnancy status unknown.\nDRUG INTERACTIONS: Cannot assess without complete medication list.\nCLINICIAN REVIEW REQUIRED: Yes. URGENTLY. Missing critical diagnostic tests for PE, pneumonia, and other serious causes.\nSAFETY NOTES: Inadequate workup increases mortality risk. Pregnancy status essential (OCP use raises VTE risk). Imaging and labs must precede any management decision.",
    },
}

PROMPTS = {
    "v1_unstructured": {
        "name": "Unstructured narrative (baseline)",
    },
    "v2_structured": {
        "name": "Structured with sections",
    },
    "v3_safety_first": {
        "name": "Safety-focused with explicit review boundaries",
    },
}

TEST_CASES = [
    {
        "id": "case_1_simple",
        "name": "Simple hypertension",
        "context": """Patient: Maria Santos, 55-year-old female
Chief Complaint: Hypertension screening visit
Vitals: BP 158/94, HR 72, RR 16, Temp 98.6F
Labs: K+ 4.1, Cr 0.9, eGFR 78
Current Medications: None
History: No prior cardiology, nonsmoker, sedentary""",
    },
    {
        "id": "case_2_complex",
        "name": "Multiple comorbidities with polypharmacy",
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
        "name": "Incomplete data requiring clarification",
        "context": """Patient: Ana Cardoso, 38-year-old female
Chief Complaint: Dyspnea on exertion x 1 week
Vitals: BP 118/76, HR 92, RR 22, Temp 99.2F
Labs: WBC 12.1 [pending CXR, D-dimer not ordered]
Current Medications: OCPs (dose unknown), antihistamine PRN
History: No prior cardiac disease, patient reports "usual allergies"
Recent: Returned from trip to rural area 10 days ago, denies travel pneumonia exposure""",
    },
]


def get_mock_output(prompt_version: str, case_id: str) -> str:
    """Get mock output for demonstration."""
    return MOCK_OUTPUTS.get(prompt_version, {}).get(case_id, "Unable to generate brief.")


def evaluate_brief(brief: str, criteria: list[str]) -> dict[str, Any]:
    """Quick evaluation of brief quality against criteria."""
    results = {}
    brief_lower = brief.lower()

    criteria_map = {
        "has_vitals": ["bp", "hr", "temp", "rr"],
        "has_labs": ["labs", "k+", "cr", "eGFR", "wbc", "hgb"],
        "has_assessment": ["assessment", "impression", "diagnosis", "status"],
        "has_action": ["next", "recommend", "action", "follow", "review"],
        "explicit_uncertainty": ["unclear", "missing", "unknown", "pending", "not provided", "requires"],
    }

    for criterion in criteria:
        if criterion in criteria_map:
            keywords = criteria_map[criterion]
            results[criterion] = any(kw.lower() in brief_lower for kw in keywords)
        else:
            results[criterion] = "unknown"

    return results


def main():
    """Run workflow: generate briefs across all prompt versions, evaluate, save results."""
    output_dir = Path(__file__).parent / "outputs"
    output_dir.mkdir(exist_ok=True)

    evaluation_criteria = [
        "has_vitals",
        "has_labs",
        "has_assessment",
        "has_action",
        "explicit_uncertainty",
    ]

    all_results = {
        "metadata": {
            "course": "BU.330.760.41 - Generative AI in Business",
            "assignment": "HW2 - Build and Evaluate Simple GenAI Workflow",
            "task": "Clinical brief generation with prompt iteration",
            "prompt_versions": list(PROMPTS.keys()),
            "evaluation_criteria": evaluation_criteria,
            "note": "Mock outputs for demonstration. In production, these would come from Claude API calls.",
        },
        "test_cases": [],
    }

    for test_case in TEST_CASES:
        print(f"\nProcessing: {test_case['name']} ({test_case['id']})")

        case_result = {
            "case_id": test_case["id"],
            "case_name": test_case["name"],
            "context": test_case["context"],
            "briefs": [],
        }

        for prompt_version in PROMPTS.keys():
            print(f"  Generating with {PROMPTS[prompt_version]['name']}...")
            brief = get_mock_output(prompt_version, test_case["id"])
            evaluation = evaluate_brief(brief, evaluation_criteria)

            case_result["briefs"].append(
                {
                    "version": prompt_version,
                    "version_name": PROMPTS[prompt_version]["name"],
                    "output": brief,
                    "evaluation": evaluation,
                }
            )

        all_results["test_cases"].append(case_result)

    output_file = output_dir / "evaluation_results.json"
    with open(output_file, "w") as f:
        json.dump(all_results, f, indent=2)

    print(f"\nResults saved to {output_file}")
    print_summary(all_results)


def print_summary(results: dict[str, Any]):
    """Print evaluation summary."""
    print("\n" + "=" * 70)
    print("EVALUATION SUMMARY")
    print("=" * 70)

    for test_case in results["test_cases"]:
        print(f"\nCase: {test_case['case_name']}")
        print("-" * 70)

        for brief in test_case["briefs"]:
            print(f"\n{brief['version_name']}:")
            eval_results = brief["evaluation"]
            passed = sum(1 for v in eval_results.values() if v is True)
            total = len([v for v in eval_results.values() if v is not True])
            print(f"  Criteria met: {passed}/{total}")
            for criterion, result in eval_results.items():
                status = "✓" if result else "✗"
                print(f"    {status} {criterion}")


if __name__ == "__main__":
    main()
