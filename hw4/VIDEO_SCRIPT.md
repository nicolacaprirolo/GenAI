# HW4 Video Walkthrough Script (2-3 minutes)

Target length: 2:50. Talking notes for screen-recorded walkthrough.

## Setup before recording
- Terminal open in `hw4/pii-detector/`
- Editor showing `SKILL.md`, `detect.py`, `semantic_detector.py`, `fix.py` in tabs
- Ollama running with `devstral:latest`

## Scene 1: Why this skill exists (0:00-0:25)

> "I work in healthtech. LGPD and HIPAA compliance means PII can never end up in a commit, a log, or an LLM prompt. Existing DLP tools target enterprise security teams, not individual developers. I built a Claude Code skill that does fast, local PII detection and replacement, designed for the developer at the keyboard."

Show: open `SKILL.md`, point to the metadata header and "When to use" section.

## Scene 2: The three-layer architecture (0:25-1:00)

> "The skill has three layers. detect.py is regex-based, fast, no LLM needed. semantic_detector.py adds an LLM layer that catches names and free-text PII the regex can't see. fix.py replaces every finding with a synthetic equivalent that has the same format."

Show: terminal `ls -la` to show file structure, then briefly open each file.

## Scene 3: Run the regex detector (1:00-1:30)

> "First the regex pass on a sample patient demo file."

Run:
```bash
python3 detect.py examples/patient_demo.py
```

Show: terminal output with 13 findings across CPF, email, phone, SSN, date of birth, credit card, API key.

> "Each finding shows the line, the pattern type, and the matched text. CPF numbers are validated with check-digit logic so we don't flag random 11-digit IDs as taxpayer numbers."

## Scene 4: Run the semantic detector (1:30-2:00)

> "Now the LLM layer on a narrative file with names and addresses the regex can't catch."

Run:
```bash
python3 semantic_detector.py --model devstral:latest examples/patient_narrative.txt
```

Show: 4 findings, names, address, contextual ID, and the daughter Ana flagged because she's a minor.

> "This catches semantic PII a regex never could, including the fact that 'his daughter Ana, age 8' identifies a minor and needs special handling under both LGPD and COPPA."

## Scene 5: Replace with synthetic data (2:00-2:30)

> "Now the fix mode. It runs the detector, then replaces every finding with a synthetic value that has the same format. Synthetic CPFs are Luhn-valid, synthetic emails use example.com, synthetic phones use the 555-prefix convention."

Run:
```bash
python3 fix.py examples/patient_demo.py
diff examples/patient_demo.py examples/patient_demo.py.cleaned | head -10
```

Show: the diff with original vs synthetic values side by side.

## Scene 6: Precision and recall (2:30-2:50)

> "Quality metric: I evaluate against labeled ground truth across four files including a negative test set of things that look like PII but aren't. Current scores: precision 1.0, recall 1.0, F1 1.0. The all-zeros filter catches obvious templates like '000-00-0000'."

Run:
```bash
python3 tests/evaluate.py
```

Show: per-file metrics and overall P/R/F1 = 1.0.

> "Honest evaluation: 1.0 across the board today, but the negative test set is small. In production I'd expect F1 around 0.95 once we add semantic detection to the metric. Code, evaluation, and Claude Code integration transcript are all in the repo. Thanks."

## Live demo backup

If recorder doesn't have Ollama:
```bash
python3 semantic_detector.py --mock examples/patient_narrative.txt
```

Mock mode uses pre-recorded findings to produce the same demonstration without an LLM call.

## Key talking points

- The skill is layered: fast regex, optional LLM, deterministic fix
- Synthetic replacements preserve format (Luhn-valid CPF, example.com emails)
- The all-zeros template filter is a small but real engineering decision
- Pre-commit hook integration possible (one example in CLAUDE_CODE_INTEGRATION.md)
- All test data is synthetic; no real patient information was used
