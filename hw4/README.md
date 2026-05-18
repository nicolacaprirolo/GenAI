## 🎥 Video Walkthrough

**[▶️ Watch on Loom](PASTE_LOOM_LINK_HERE)**

Link: PASTE_LOOM_LINK_HERE

---

# HW4 (Week 5): PII Detector Skill

A reusable Claude Code skill that scans code, logs, and text for personally identifiable information. Submission for BU.330.760.41 Homework 4 by Nicola Capriolo Teran.

## Rubric Mapping

| Rubric requirement | File / location |
|--------------------|-----------------|
| Skill folder under `.claude/skills/` | `.claude/skills/pii-detector/` |
| SKILL.md with frontmatter (name + description) | `.claude/skills/pii-detector/SKILL.md` |
| Script in `scripts/` subdirectory | `.claude/skills/pii-detector/scripts/detect.py` |
| README with video link | this file |
| Optional `references/` | `.claude/skills/pii-detector/references/CLAUDE_CODE_INTEGRATION.md` |

## What This Skill Does

Scans a file (code, log, free text) and finds PII patterns. Three layers:

| Layer | Script | Purpose |
|-------|--------|---------|
| 1 | `detect.py` | Deterministic regex + Luhn check + CPF mod-11 validation |
| 2 | `semantic_detector.py` | LLM layer for names, addresses, free-text PHI the regex cannot see |
| 3 | `fix.py` | Replaces every finding with a synthetic equivalent that preserves the format |

The deterministic script is genuinely load-bearing. A prompt alone cannot run Luhn validation on credit card numbers or compute Brazilian CPF check digits with modulo-11 arithmetic. Those calculations need code.

## Why I Chose This Skill

I work in healthtech. LGPD (Brazil) and HIPAA (US) compliance means PII cannot leak into commits, logs, or LLM prompts. Commercial DLP tools target enterprise security teams. This skill targets the developer at the keyboard with a fast local scanner that runs before commit, before sharing logs, or before pasting context into an LLM.

The narrow scope (PII patterns, not arbitrary content) makes it reusable across any codebase that handles regulated data.

## Folder Structure

```
hw4/
├── README.md                                      (this file, video link at top)
├── .claude/
│   └── skills/
│       └── pii-detector/
│           ├── SKILL.md                           (skill manifest with frontmatter)
│           ├── scripts/
│           │   ├── detect.py                      (LAYER 1: regex detector)
│           │   ├── semantic_detector.py           (LAYER 2: LLM detector)
│           │   └── fix.py                         (LAYER 3: synthetic replacement)
│           └── references/
│               └── CLAUDE_CODE_INTEGRATION.md     (usage transcript)
├── examples/                                      (test files: positive + negative + narrative)
│   ├── clean_code.py
│   ├── version_string_traps.py
│   ├── mixed_log.txt
│   ├── patient_demo.py
│   └── patient_narrative.txt
├── tests/
│   ├── evaluate.py                                (P/R/F1 evaluator)
│   └── evaluation_results.json
├── EVALUATION.md                                  (methodology and results)
├── VIDEO_SCRIPT.md                                (talking notes for the recording)
├── requirements.txt
└── .gitignore
```

## How To Use (Three Test Prompts)

The rubric requires testing on at least 3 prompts: one normal, one edge case, one cautious case.

### 1. Normal case (regex detection)

```bash
python3 .claude/skills/pii-detector/scripts/detect.py examples/patient_demo.py
```

Returns 13 findings across 7 pattern types (CPF, email, phone, SSN, date of birth, credit card, API key). All valid per check-digit validation.

### 2. Edge case (semantic detection for names + addresses)

```bash
python3 .claude/skills/pii-detector/scripts/semantic_detector.py --mock examples/patient_narrative.txt
```

Catches 4 semantic findings the regex cannot see: full patient name, street address with postal code, contextual identifier ("the patient in room 304"), minor's name with age.

### 3. Cautious / negative case (avoid false positives)

```bash
python3 .claude/skills/pii-detector/scripts/detect.py examples/version_string_traps.py
```

Returns 0 findings. Strings like "000-00-0000" and "(000) 000-0000" look like SSN/phone patterns but the all-zeros filter excludes them as obvious templates.

### Bonus: Apply synthetic replacement

```bash
python3 .claude/skills/pii-detector/scripts/fix.py examples/patient_demo.py
diff examples/patient_demo.py examples/patient_demo.py.cleaned
```

Replaces every PII finding with a synthetic equivalent that preserves format (Luhn-valid synthetic CPFs, example.com emails, 555-prefix phones).

## What The Scripts Do (Deterministic Part)

`detect.py` is where prose alone cannot do the job:

- **CPF validation**: implements the Brazilian taxpayer ID check-digit algorithm (modulo 11 with multiplier sequences). The model would have to do this arithmetic in its head and would make mistakes.
- **Credit card validation**: implements the Luhn algorithm. Same reason.
- **Multi-pattern scanning**: 9 patterns with line-numbered findings. A model could approximate this but would miss matches on long files.
- **All-zeros filter**: skips obvious template strings to keep precision at 1.0.

The LLM layer (`semantic_detector.py`) is what the model is good at: free-text reasoning about whether a string in context is a person name, address, or contextual identifier.

## What Worked Well

- The three-layer architecture lets each layer do what it is good at
- Precision and recall both hit 1.0 on the labeled dataset
- Synthetic replacement preserves format so cleaned files still parse downstream
- Skill is reusable in any project: drop the `.claude/skills/pii-detector/` folder anywhere

## What Limitations Remain

- Pattern set is fixed at code-time; new PII types need code edits
- Test dataset is 4 files; production deployment would need 100+
- Mock mode for the semantic layer is convenient for grading but a live model is the real test
- No binary file support (PDFs, images, EHR exports out of scope)
- Names that are also common words ("Hope", "Faith", "Grace") may be missed by the semantic layer

## Evaluation Summary

| File | Type | TP | FP | FN | Precision | Recall | F1 |
|------|------|----|----|----|-----------|--------|----|
| clean_code.py | Negative | 0 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| version_string_traps.py | Negative (traps) | 0 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| mixed_log.txt | Mixed | 7 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| patient_demo.py | Dense PII | 13 | 0 | 0 | 1.0 | 1.0 | 1.0 |
| **OVERALL** | | **20** | **0** | **0** | **1.0** | **1.0** | **1.0** |

Full methodology in `EVALUATION.md`.
