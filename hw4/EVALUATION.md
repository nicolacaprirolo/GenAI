# HW4 Evaluation: PII Detector Skill

## Methodology

Three labeled test cases were used to measure detection precision and recall:

1. **Clean code**: a Python module with no PII. Tests false positive rate.
2. **Mixed log**: a server log with 7 PII items mixed among normal log lines. Tests detection of varied PII types in noisy context.
3. **Patient demo**: a Python module deliberately containing 13+ PII items. Tests handling of dense PII.

Each test case has expected finding counts and expected pattern types. The detector passes if it meets both criteria.

## Results

| Test Case | Expected Findings | Actual | Patterns Found | Status |
|-----------|------------------|--------|----------------|--------|
| Clean code | 0 | 0 | (none) | PASS |
| Mixed log | >=7 | 7 | CPF, DATE_OF_BIRTH, EMAIL, PHONE_BR, SSN, CNS | PASS |
| Patient demo | >=8 | 13 | API_KEY, CPF, CREDIT_CARD, DATE_OF_BIRTH, EMAIL, PHONE_BR, SSN | PASS |

Total: 3/3 test cases passed (100%)

## Key Findings

### False Positive Rate

The clean code test case contains numeric constants (version "2.1.0", retry count "3", timeout "30"), prices ("$9.99"), and structured data that could trigger pattern matches. The detector correctly identifies these as non-PII because:

- Version strings do not match phone or CPF patterns
- Prices have insufficient digits for credit card matching
- Date constants in code are typically format `2024-05-18` (ISO 8601) not the targeted DD/MM/YYYY birth-date pattern

### Detection Patterns

The mixed log test demonstrates real-world detection in noisy data. The detector picks out PII embedded in log messages while ignoring timestamps, IP addresses, and structured log metadata.

The patient demo test confirms detection scales to dense PII files. With 13+ items across 7 pattern types, the detector returned 13 findings without missing critical categories.

### Validation Logic

Two patterns use validation beyond regex matching:

- **CPF**: validates Brazilian taxpayer ID check digits (modulo 11 algorithm)
- **Credit Card**: validates with Luhn algorithm

These checks reduce false positives. For example, "123.456.789-00" passes the regex but fails the CPF check digit and is correctly excluded.

## Interpretation

The pattern-based approach is the right choice for this task because:

1. **Speed**: regex scans are sub-second on files of any reasonable size
2. **Determinism**: same input produces same output, supporting reproducible test results
3. **No API dependency**: works offline, no API costs, no network round-trips
4. **Auditability**: every match shows the exact regex that triggered, supporting debugging

A model-based approach (sending text to an LLM and asking "does this contain PII?") would catch more subtle PII (names, addresses, contextual disclosures) but at significant cost: each scan would take seconds, cost money, leak data outside the local machine, and produce non-deterministic results. For the primary use case (developer scanning code before committing), the pattern-based approach wins.

## Limitations

- Cannot detect free-text PII (names in prose, addresses, narrative health info)
- Pattern set is fixed; new PII types require code changes
- May miss internationally formatted phone numbers (only BR and US covered)
- Date patterns only match common DD/MM/YYYY format; ISO 8601 dates without slashes are not matched as birthdates
- Confidence is binary (match or no match); no probability score

## Production Considerations

For a real deployment:

- Add pre-commit hook integration so the detector runs before `git commit`
- Add CI/CD integration to scan repositories on push
- Cache detection results for unchanged files
- Add a configuration file for project-specific allowlists
- Layer an LLM scan on top for semantic detection
- Track metrics over time (issues found per month, time-to-fix)

## Conclusion

The PII detector skill is a narrow, well-scoped tool that solves one problem well: fast pattern-based PII detection for developers working with healthcare data. The 3/3 test pass rate confirms the implementation works as designed.

This implementation embodies the course philosophy of building useful narrow tools rather than broad ambitious systems. By limiting scope to pattern matching and delegating semantic detection to future work, the tool stays fast, deterministic, and auditable today while leaving room for evolution.
