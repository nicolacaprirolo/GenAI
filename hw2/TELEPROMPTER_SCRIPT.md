# HW2 Teleprompter Script (~110 seconds)

Copy the body below into CuePrompter or Teleprompter and read at a natural pace. Every rubric item is explicitly called out.

---

Hi, I'm Nico Caprirolo, MBA student at Johns Hopkins Carey and founder of Holi Labs. This is my HW2 walkthrough.

The business workflow I picked is clinical brief generation. A primary care doctor in a public hospital in Latin America sees 30 to 50 patients per shift. The input is raw patient context: vitals, labs, meds, history. The output is a structured 30-second brief a clinician can scan before walking into the room. It's a real written-communication task where a confident-but-wrong output is dangerous.

[Show eval_set.json] This is my evaluation set: five stable test cases. A normal hypertension screen, a complex multi-comorbidity case, an incomplete-data case, a pediatric edge case, and a healthy control. Each case has notes on what a good output should do, so the eval is fair and repeatable.

[Show app.py] This is app.py. It runs from the command line, makes real LLM calls through Ollama, and saves outputs to a JSON file. The prompt version is configurable with a flag.

[Show prompts.md] Here is the prompt iteration with evidence. V1 was a one-line baseline that scored 3.4 out of 10 on an LLM-as-judge rubric. V2 added a fixed format with sections, which moved the score to 7.2. V3 added two techniques from the course readings: few-shot examples in the Brown et al. style and chain-of-thought scaffolding in the Wei et al. style, plus an explicit MISSING DATA section. V3 scored 9.8 out of 10.

[Show one example output, case 3 in outputs/generation_results.json] This is one example output. On the incomplete-data case, V1 just narrated. V2 listed pending tests. V3 flagged that pregnancy status was never documented, which is critical for the differential. That's the kind of catch that turns a useful brief into a safe one.

[Switch to GitHub] On GitHub you can see the repo, all five required files (README, app.py, prompts.md, eval_set.json, report.md), and the commit history showing each step.

My honest recommendation: I would NOT deploy this without clinician validation on real charts, a regulatory review for software-as-a-medical-device, and human review on every output until calibration data exists. The prototype still fails when context is sparse, and "Clinician Review Required" appears on every V3 case, so alert fatigue is a real risk.

What I learned is that the choice of evaluator matters as much as the prompt itself. My keyword heuristic ranked V2 above V3 because of literal string matches, but the LLM-judge inverted that ranking once it measured clinical content. What surprised me is how much lift two worked examples provided for so little prompt-token cost. Thanks.

---

## Rubric Coverage (every item explicitly hit)

| Rubric item | Where in script |
|------------|-----------------|
| Workflow defined | Paragraph 2 |
| User identified | Paragraph 2 ("primary care doctor in a public hospital in Latin America") |
| Input / output described | Paragraph 2 |
| Why valuable | Paragraph 2 ("30 to 50 patients per shift", "confident-but-wrong is dangerous") |
| Eval set, 5 cases incl. normal + edge | Paragraph 3 |
| Working prototype + real LLM call | Paragraph 4 |
| Configurable prompt | Paragraph 4 ("configurable with a flag") |
| Saved outputs | Paragraph 4 ("saves outputs to a JSON file") |
| ≥2 prompt revisions + evidence | Paragraph 5 (V1=3.4, V2=7.2, V3=9.8) |
| Example output | Paragraph 6 (Case 3 pregnancy-status catch) |
| GitHub repo + commits | Paragraph 7 |
| Honest deploy recommendation | Paragraph 8 |
| Human review boundaries | Paragraph 8 |
| What you learned | Paragraph 9 |
| What surprised you | Paragraph 9 |

## Style Compliance

- No em dashes
- No forbidden words (align/enable/enhance/robust/ensure/highlight)
- No "not X, but Y" patterns
- No paragraphs ending with a citation

## Recording Timing

Target: 110 seconds. Read at conversational pace, not rushed. The script has 9 paragraphs averaging ~12 seconds each.
