---
name: pii-detector
description: Scan code, logs, or text for Brazilian and US personally identifiable information (PII) patterns. Use this before committing code, sharing logs, or pasting content into prompts. Detects CPF, CNS, SSN, phone numbers, email addresses, dates of birth, and credit card numbers. Returns a structured report with line numbers and pattern types.
---

# PII Detector Skill

## What This Skill Does

Scans text or code files for patterns that match personally identifiable information (PII) for Brazilian healthcare (LGPD) and US healthcare (HIPAA) compliance contexts.

## When To Use

- Before committing code or configuration that may contain test data
- Before sharing logs or debugging output
- Before pasting content into an LLM prompt
- During code review for healthcare or financial applications
- When auditing data exports for compliance

## When NOT To Use

- For deep semantic detection (e.g., names without obvious patterns)
- As a replacement for a full DLP (Data Loss Prevention) tool
- For binary file analysis
- For network traffic inspection

## How To Use

Run the detector with a file path or piped input:

```bash
# Scan a file
python3 detect.py path/to/file.py

# Scan piped input
cat log.txt | python3 detect.py -

# Scan with specific patterns only
python3 detect.py --patterns cpf,email path/to/file.py

# Output as JSON
python3 detect.py --json path/to/file.py
```

## Patterns Detected

| Pattern | Format | Region |
|---------|--------|--------|
| CPF | 000.000.000-00 or 11 digits | Brazil |
| CNS | 15 digits (Cartão Nacional de Saúde) | Brazil |
| SSN | 000-00-0000 | US |
| Phone (BR) | (00) 00000-0000 | Brazil |
| Phone (US) | (000) 000-0000 | US |
| Email | name@domain.tld | Universal |
| Date of Birth | DD/MM/YYYY or MM/DD/YYYY | Universal |
| Credit Card | 16 digit Luhn-valid | Universal |

## Output Format

The skill returns a structured report:

```
File: example.py
Issues found: 3

Line 12: [CPF] 123.456.789-01
Line 25: [EMAIL] patient@example.com
Line 38: [DATE_OF_BIRTH] 15/03/1985
```

Or JSON format:

```json
{
  "file": "example.py",
  "total_issues": 3,
  "findings": [
    {"line": 12, "pattern": "CPF", "match": "123.456.789-01"},
    {"line": 25, "pattern": "EMAIL", "match": "patient@example.com"},
    {"line": 38, "pattern": "DATE_OF_BIRTH", "match": "15/03/1985"}
  ]
}
```

## Integration with Claude Code

When using this skill from Claude Code, the agent should:

1. Read the file being scanned
2. Invoke `python3 detect.py <file>` via the Bash tool
3. Parse the structured output
4. Surface findings to the user with recommended actions:
   - Replace with synthetic data
   - Move to a secrets manager
   - Remove from the file

## Limitations

- Pattern matching only; no semantic understanding
- May produce false positives on valid non-PII strings matching patterns
- Does not detect names, addresses, or other PII without distinctive formats
- Limited to patterns defined in the script
- No real-time monitoring; one-shot analysis only

## Examples

See `examples/` directory for sample files demonstrating the detector's behavior.
