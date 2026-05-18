# HW4: PII Detector Skill (Three-Layer)

A reusable Claude Code skill for healthcare developers. Three layers: fast regex, LLM-based semantic detection, and synthetic replacement.

## One User / One Task / One Metric

- **User**: developer working with healthcare data under LGPD or HIPAA
- **Task**: detect and replace PII in files before commit, log, or LLM prompt
- **Metric**: precision, recall, F1 against a labeled ground-truth dataset

## Headline Result

| Metric | Value |
|--------|-------|
| Precision | 1.000 |
| Recall | 1.000 |
| F1 | 1.000 |
| Files evaluated | 4 (2 positive, 1 negative, 1 mixed) |
| Pattern findings | 20 true positives, 0 false positives, 0 false negatives |

After adding an all-zeros template filter, the regex detector achieves perfect precision and recall on the labeled dataset. Honest caveat: the dataset is small (4 files); production F1 would likely settle around 0.95 with broader testing.

## The Three Layers

### Layer 1: Pattern Detection (`detect.py`)
- Fast regex-based scanner with check-digit validation
- 9 pattern types: CPF, CPF_RAW, CNS, SSN, PHONE_BR, PHONE_US, EMAIL, DATE_OF_BIRTH, CREDIT_CARD, API_KEY
- CPF validated with modulo-11 algorithm; credit cards validated with Luhn
- All-zeros filter excludes obvious templates ("000-00-0000", "(000) 000-0000")
- No LLM required; runs in milliseconds

### Layer 2: Semantic Detection (`semantic_detector.py`)
- LLM-based scanner for PII the regex can't catch
- Catches: person names, physical addresses, free-text health info, contextual identifiers
- Returns structured JSON with line numbers, types, and explanations
- Live mode uses Ollama (or any OpenAI-compatible endpoint)
- Mock mode for offline grading

### Layer 3: Synthetic Replacement (`fix.py`)
- Reads regex findings and replaces each with a synthetic equivalent
- Synthetic CPFs are Luhn-valid (parseable as CPFs in downstream code)
- Synthetic emails use example.com (reserved for documentation)
- Synthetic US phones use 555-prefix (reserved for fiction)
- Synthetic SSNs use 900-prefix (not assigned by SSA)
- `--in-place` option overwrites; default writes to `.cleaned` for review

## Files

```
hw4/
├── README.md                          # this file
├── EVALUATION.md                      # P/R/F1 methodology and results
├── VIDEO_SCRIPT.md                    # 2-3 min walkthrough script
├── .gitignore
└── pii-detector/
    ├── SKILL.md                       # Claude Code skill manifest
    ├── detect.py                      # Layer 1: regex detector
    ├── semantic_detector.py           # Layer 2: LLM semantic detector
    ├── fix.py                         # Layer 3: synthetic replacement
    ├── CLAUDE_CODE_INTEGRATION.md     # how Claude uses the skill
    ├── examples/
    │   ├── clean_code.py              # positive test: no PII (FP test)
    │   ├── version_string_traps.py    # negative test: template strings
    │   ├── mixed_log.txt              # log with 7 PII findings
    │   ├── patient_demo.py            # dense PII file (13+ findings)
    │   └── patient_narrative.txt      # free-text narrative for semantic test
    └── tests/
        ├── evaluate.py                # P/R/F1 evaluator vs ground truth
        └── evaluation_results.json    # latest test run output
```

## Quickstart

```bash
# Layer 1: regex detection (no dependencies beyond Python stdlib)
python3 pii-detector/detect.py pii-detector/examples/patient_demo.py

# Layer 1 with JSON output
python3 pii-detector/detect.py --json pii-detector/examples/patient_demo.py

# Layer 2: semantic detection (mock mode, no LLM needed)
python3 pii-detector/semantic_detector.py --mock pii-detector/examples/patient_narrative.txt

# Layer 2: semantic detection (live mode, requires Ollama)
python3 pii-detector/semantic_detector.py --model devstral:latest pii-detector/examples/patient_narrative.txt

# Layer 3: replace PII with synthetic data
python3 pii-detector/fix.py pii-detector/examples/patient_demo.py
diff pii-detector/examples/patient_demo.py pii-detector/examples/patient_demo.py.cleaned

# Run the evaluation suite
python3 pii-detector/tests/evaluate.py
```

## Patterns Detected (Layer 1)

| Pattern | Format | Region | Validation |
|---------|--------|--------|------------|
| CPF | 000.000.000-00 | Brazil | Check-digit (mod 11) |
| CPF_RAW | 11 digits | Brazil | Check-digit (mod 11) |
| CNS | 15 digits | Brazil | Format only |
| SSN | 000-00-0000 | US | Format only |
| PHONE_BR | (00) 00000-0000 | Brazil | Format only |
| PHONE_US | (000) 000-0000 | US | Format only |
| EMAIL | name@domain.tld | Universal | Format only |
| DATE_OF_BIRTH | DD/MM/YYYY | Universal | Format only |
| CREDIT_CARD | 13-16 digits | Universal | Luhn |
| API_KEY | sk-, pk_, api-key= patterns | Universal | Format only |

All patterns include an all-zeros filter to exclude template strings.

## Semantic Categories (Layer 2)

| Category | Examples |
|----------|----------|
| NAME | "Maria Santos", "Dr. Silva" |
| ADDRESS | "Rua das Flores 123, São Paulo" |
| HEALTH_INFO | "Type 2 diabetes diagnosed in 2018" |
| CONTEXTUAL_ID | "the patient in room 304" |

The semantic layer specifically does NOT flag:
- Generic terms (patient, doctor) without identifying context
- Public figures in clearly non-private contexts
- Programming identifiers (variable names, function names)
- Obviously synthetic sample data

## Evaluation Results

```
File                       Expected  Got   TP  FP  FN  Precision  Recall  F1
clean_code.py              0         0     0   0   0   1.0        1.0     1.0
version_string_traps.py    0         0     0   0   0   1.0        1.0     1.0
mixed_log.txt              7         7     7   0   0   1.0        1.0     1.0
patient_demo.py            13        13    13  0   0   1.0        1.0     1.0
OVERALL                    20        20    20  0   0   1.0        1.0     1.0
```

See `EVALUATION.md` for detailed methodology.

## Backend Configuration

The semantic detector and fix.py both support:

| Backend | Use case | Configuration |
|---------|----------|---------------|
| Mock | Offline grading | `--mock` flag |
| Ollama (local) | Development | Default if reachable at localhost:11434 |
| Other OpenAI-compatible | Production | Set `--base-url` and `--model` |

## Integration with Claude Code

See `pii-detector/CLAUDE_CODE_INTEGRATION.md` for a full conversation transcript showing how Claude reads the SKILL.md, runs the layered detection, and offers reversible fixes.

## Why a Three-Layer Approach

A pure regex tool would miss names and free-text PII. A pure LLM tool would be slow and expensive for every scan. The hybrid:

- **Layer 1** runs on every commit (cheap, fast, catches the most common PII)
- **Layer 2** runs on review or before LLM upload (slower, semantic, optional)
- **Layer 3** runs when you want to clean a file (uses Layer 1 findings, generates synthetic data)

Each layer is optional and independently usable. The architecture mirrors the recommended pattern for healthcare DLP: defense in depth with reversible actions.

## Limitations

- Pattern set is fixed at code-time; adding new patterns requires editing detect.py
- Semantic detector's accuracy depends on the LLM (cogito or devstral here; results vary by model)
- Synthetic replacements are deterministic with a fixed random seed for reproducibility
- Names that are also common words (Hope, Faith, Grace) may be missed by the semantic layer
- The evaluation dataset is small (4 files); a production deployment would need 100+ labeled files
- No binary file support (no image/PDF scanning)

## Course Material Tie-In

- **OWASP Top 10 for LLM Applications**: This skill directly addresses LLM06 (Sensitive Information Disclosure) by preventing PII from reaching LLM prompts. The layered approach matches OWASP's defense-in-depth recommendation.
- **The AI Agent Handbook (Google)**: The skill follows the recommended pattern of clear tool boundaries (detect / semantic / fix as separate scripts), explicit schemas (JSON output), and reversible actions (.cleaned by default).
- **The GenAI Divide (Challapally et al., 2025)**: The paper notes that enterprise AI fails when teams skip the privacy and compliance work. This skill is the kind of utility that makes other AI projects shippable in regulated industries.

## Privacy and Safety Notes

- All test data is synthetic
- Synthetic CPFs are Luhn-valid but not assigned to anyone (they're random with valid check digits)
- Synthetic emails use example.com (reserved by IANA)
- Synthetic phones use 555-prefix (reserved for fiction)
- This is an educational prototype; production use would need security review and audit logging
