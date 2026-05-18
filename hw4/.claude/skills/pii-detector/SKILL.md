---
name: pii-detector
description: Scans code, logs, or free text for personally identifiable information including Brazilian CPF/CNS, US SSN, phone numbers, emails, dates of birth, credit cards, and API keys. Use when the user asks to check, scan, audit, or clean a file for PII before committing, sharing logs, or pasting content into an LLM prompt. Validates findings with Luhn algorithm and CPF mod-11 check digits to reduce false positives. Also offers an optional LLM layer for semantic PII (names, addresses) and a fix mode that replaces findings with format-preserving synthetic values.
---

# PII Detector Skill

## What This Skill Does

A three-layer scanner for personally identifiable information (PII) in healthcare, financial, and developer contexts. The deterministic regex layer is the load-bearing core. Optional LLM and synthetic-replacement layers extend its utility.

## When To Use

- Before `git commit` on any file that may contain test data
- Before sharing logs or debugging output
- Before pasting content into an LLM prompt
- During code review for healthcare (LGPD, HIPAA) or financial applications
- When the user asks to "scan", "check", "audit", "clean", "redact", or "find PII" in a file

## When NOT To Use

- For binary files (PDFs, images, EHR exports)
- As a replacement for a full DLP (Data Loss Prevention) tool
- For real-time network traffic inspection
- For arbitrary content moderation beyond PII patterns

## Available Scripts

| Script | Layer | Purpose |
|--------|-------|---------|
| `scripts/detect.py` | 1 (regex) | Fast deterministic pattern detection with Luhn + CPF validation |
| `scripts/semantic_detector.py` | 2 (LLM) | Catches names, addresses, free-text PHI that regex cannot see |
| `scripts/fix.py` | 3 (replacement) | Generates synthetic replacements that preserve format |

## How To Use From An Agent

When called from a coding assistant (Claude Code, Codex, etc.) running from the project root:

```bash
# Layer 1: regex detection (no API key needed)
python3 .claude/skills/pii-detector/scripts/detect.py path/to/file.py

# Layer 1 with JSON output for downstream parsing
python3 .claude/skills/pii-detector/scripts/detect.py --json path/to/file.py

# Layer 2: semantic detection (uses Ollama by default, --mock for offline)
python3 .claude/skills/pii-detector/scripts/semantic_detector.py --mock path/to/file.py

# Layer 3: replace PII with synthetic values
python3 .claude/skills/pii-detector/scripts/fix.py path/to/file.py
```

## Three Test Cases (Required by Rubric)

The skill ships with three test cases at the project root under `examples/`:

| Case Type | File | Expected Behavior |
|-----------|------|-------------------|
| Normal | `examples/patient_demo.py` | Returns 13 findings across 7 pattern types |
| Edge (semantic) | `examples/patient_narrative.txt` | Layer 2 catches 4 free-text PII items the regex misses |
| Cautious (negative) | `examples/version_string_traps.py` | Returns 0 findings; the all-zeros filter excludes obvious templates |

## Patterns Detected (Layer 1)

| Pattern | Format | Region | Validation |
|---------|--------|--------|------------|
| CPF | 000.000.000-00 | Brazil | Modulo-11 check digits |
| CPF_RAW | 11 raw digits | Brazil | Modulo-11 check digits |
| CNS | 15 digits | Brazil | Format only |
| SSN | 000-00-0000 | US | Format only |
| Phone (BR) | (00) 00000-0000 | Brazil | Format only |
| Phone (US) | (000) 000-0000 | US | Format only |
| Email | name@domain.tld | Universal | RFC-style pattern |
| Date of Birth | DD/MM/YYYY | Universal | Format only |
| Credit Card | 13-16 digits | Universal | Luhn algorithm |
| API Key | sk-, pk_, api-key= patterns | Universal | Format only |

All patterns skip matches where the digits are all zeros, which catches obvious placeholders like `000-00-0000`.

## Output Format

Plain text by default:

```
File: example.py
Issues found: 3

Line 12: [CPF] 123.456.789-01
  Context: "cpf": "123.456.789-01",

Line 25: [EMAIL] patient@example.com
  Context: "email": "patient@example.com",
```

JSON with `--json` flag:

```json
{
  "file": "example.py",
  "total_issues": 3,
  "findings": [
    {"line": 12, "pattern": "CPF", "match": "123.456.789-01", "context": "..."},
    {"line": 25, "pattern": "EMAIL", "match": "patient@example.com", "context": "..."}
  ]
}
```

## Integration Recommendation for Agents

When an agent finds PII via this skill, the appropriate next steps are:

1. List findings to the user with line numbers and pattern types
2. For each finding, suggest one of:
   - Replace with a synthetic equivalent via `scripts/fix.py` (recommended for test data)
   - Move to a secrets manager (recommended for API keys)
   - Delete the line entirely (recommended for real PII that should not exist in the file)
3. Wait for user approval before modifying the file
4. Re-run the scanner after fixes to confirm zero remaining findings

See `references/CLAUDE_CODE_INTEGRATION.md` for a complete worked transcript of an agent session using this skill.

## Limitations

- Pattern matching only; Layer 1 cannot detect names without distinctive formats
- May produce false positives on valid non-PII strings matching the patterns
- Layer 2 (semantic) requires an LLM and is slower than Layer 1
- No binary file support
- No real-time monitoring; one-shot analysis only
- Layer 3 (fix mode) writes to `<file>.cleaned` by default; user must explicitly approve overwrite

## Privacy and Safety Notes

- All example files use synthetic data; no real PHI is included
- Synthetic CPF replacements are Luhn-valid but unassigned (random with valid check digits)
- Synthetic emails use example.com (reserved by IANA)
- Synthetic phones use 555-prefix (reserved for fiction)
