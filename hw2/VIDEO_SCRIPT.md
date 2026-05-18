# HW2 Video Walkthrough Script (2-3 minutes)

Target length: 2:30. Talking notes for screen-recorded walkthrough.

## Setup before recording
- Terminal open in `hw2/` directory
- Editor with `brief_generator.py`, `llm_judge.py`, `ITERATION_LOG.md` visible in tabs
- `outputs/` directory cleared

## Scene 1: Problem framing (0:00-0:25)

> "I work in clinical decision support for emerging markets. The problem I picked for HW2 is clinician brief generation: a primary care doctor in a public hospital sees 40 patients per shift and needs a 30-second summary of each patient before the visit. I built three prompt versions and evaluated them rigorously."

Show: open `brief_generator.py` in editor.

## Scene 2: Three prompt versions (0:25-0:55)

> "V1 is a baseline, one line asking for a summary. V2 adds a fixed format with sections. V3 adds two things from the course readings: few-shot examples from Brown et al. and chain-of-thought reasoning from Wei et al. Plus a safety-first framing."

Show: scroll through `PROMPTS` list in `brief_generator.py`, then briefly show the V3 prompt with its two worked examples.

## Scene 3: Run the generator (0:55-1:25)

> "Let me run it on five synthetic cases, normal, complex, ambiguous, edge, and a healthy control. Mock mode uses pre-recorded outputs so the grader can reproduce without an API key."

Run:
```bash
python3 brief_generator.py --mock
```

Show: terminal output with the heuristic scores. Point out V2 looks like it's winning on keyword matching.

## Scene 4: Run the LLM-as-judge (1:25-1:55)

> "But keyword matching is a weak evaluator. I added an LLM-as-judge that scores each brief on five clinical dimensions. Now look at the spread."

Run:
```bash
python3 llm_judge.py --mock
```

Show: judge summary table. Point out the inversion, V3 dominates 9.80, V2 7.20, V1 3.40.

## Scene 5: Why V3 wins (1:55-2:20)

Open `ITERATION_LOG.md`.

> "V3 wins on uncertainty handling and safety posture, which are the two dimensions clinicians actually need. Case 3, incomplete data, V1 just narrated, V2 listed pending tests, but V3 flagged that pregnancy status was never documented and that's critical for the differential. That's the kind of catch that makes the difference between a useful brief and a malpractice risk."

## Scene 6: Limitations and next steps (2:20-2:30)

> "Limitations: I evaluated on five synthetic cases, not real charts. The LLM-as-judge has its own biases. Next step would be clinician validation on a held-out set. Code, eval results, and the iteration log are all in the repo. Thanks."

## Live demo backup

If the recording happens with Ollama running and time permits, swap mock mode for live:
```bash
python3 brief_generator.py --case case_4_edge_pediatric --version v3_fewshot_cot --model devstral:latest
```

This shows the real LLM producing a brief on the fly, which is more compelling than mock outputs.
