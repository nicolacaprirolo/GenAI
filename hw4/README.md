# HW4: PII Detector Skill

A reusable Claude Code skill that scans code, logs, and text for personally identifiable information (PII).

## The One User / One Task / One Metric Frame

- **User**: developer working with healthcare data (Brazilian LGPD or US HIPAA context)
- **Task**: scan a file for PII before committing, sharing, or pasting into a prompt
- **Metric**: detection precision and recall on labeled test cases

## Why This Skill

Healthcare engineers regularly work with patient data. Before committing code, sharing logs, or pasting context into an LLM, they need fast feedback on whether the file contains PII. Manual review is slow and error-prone. Existing DLP tools target enterprise security teams, not individual developers in their editor.

This skill fills that gap with a fast, local, pattern-based scanner that works as a standalone CLI or as a Claude Code skill.

## Skill Architecture

```
hw4/pii-detector/
├── SKILL.md          # Skill manifest with metadata and usage
├── detect.py         # CLI scanner implementation
├── examples/         # Sample files demonstrating clean vs PII-heavy content
│   ├── clean_code.py
│   ├── mixed_log.txt
│   └── patient_demo.py
└── tests/
    ├── evaluate.py   # Automated test runner
    └── evaluation_results.json  # Latest test run output
```

## Patterns Detected

| Pattern | Format | Region |
|---------|--------|--------|
| CPF | 000.000.000-00 (with Luhn validation) | Brazil |
| CNS | 15 digits | Brazil |
| SSN | 000-00-0000 | US |
| Phone (BR) | (00) 00000-0000 | Brazil |
| Phone (US) | (000) 000-0000 | US |
| Email | name@domain.tld | Universal |
| Date of Birth | DD/MM/YYYY | Universal |
| Credit Card | 13-16 digits with Luhn validation | Universal |
| API Key | Stripe (sk-), OpenAI, Anthropic, generic | Universal |

## Usage

### Direct CLI

```bash
# Scan a file
python3 detect.py path/to/file.py

# Pipe stdin
cat log.txt | python3 detect.py -

# Output JSON for downstream processing
python3 detect.py --json path/to/file.py

# Filter to specific patterns
python3 detect.py --patterns CPF,EMAIL path/to/file.py

# List available patterns
python3 detect.py --list-patterns
```

### As a Claude Code Skill

In a Claude Code session, the agent can invoke this skill by:

1. Reading the file being scanned
2. Running `python3 pii-detector/detect.py <file>` via Bash
3. Parsing the structured output
4. Suggesting fixes for each finding

## Evaluation

Run the test suite:

```bash
python3 tests/evaluate.py
```

Current results: **3 / 3 test cases passed**

Test cases:
1. **Clean code** (`clean_code.py`): expects 0 findings, validates false positive rate
2. **Mixed log** (`mixed_log.txt`): expects at least 7 findings across 5 pattern types
3. **Patient demo** (`patient_demo.py`): expects at least 8 findings across 7 pattern types

## Demonstration Workflow

```bash
# 1. Scan a sample patient file
python3 pii-detector/detect.py pii-detector/examples/patient_demo.py

# 2. Scan a clean file (should report 0 findings)
python3 pii-detector/detect.py pii-detector/examples/clean_code.py

# 3. Pipe a log through the scanner
cat pii-detector/examples/mixed_log.txt | python3 pii-detector/detect.py -

# 4. Get JSON for tooling integration
python3 pii-detector/detect.py --json pii-detector/examples/patient_demo.py
```

## How This Integrates with a Coding Assistant

When the user asks Claude Code to "check this file for PII", the agent should:

1. Identify the target file
2. Execute the skill via Bash
3. Parse findings
4. For each finding, suggest one of:
   - Replace with a synthetic placeholder
   - Move to a secrets manager
   - Delete entirely
5. Apply the user-approved fix

The skill produces machine-readable JSON output specifically to make this integration straightforward.

## Limitations

- Pattern-based detection only; cannot detect names, addresses, or unusual PII formats
- May produce false positives on numeric data matching pattern lengths
- CPF and credit card validators reduce false positives but are not perfect
- Does not scan binary files
- No memory of previous scans; one-shot analysis

## Course Reference

This skill embodies the narrow-scope approach demonstrated in the CardioPrep example: one user, one task, one metric. The implementation favors a deterministic Python script over a model-based detector because pattern matching is fast, auditable, and does not require an API key for every scan.

A future version could layer an LLM on top to detect semantic PII (names without distinctive formats, addresses, free-text health information). The current pattern-based version provides a fast first pass that catches the most common patterns with high precision.
