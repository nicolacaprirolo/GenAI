# Using the PII Detector as a Claude Code Skill

A complete transcript showing how the skill integrates into a coding workflow.

## Setup

Place this skill folder inside your project (or in `~/.claude/skills/`). The `SKILL.md` file is the entry point Claude reads to understand the skill's purpose.

```
.claude/skills/pii-detector/
├── SKILL.md
├── detect.py
├── semantic_detector.py
├── fix.py
├── examples/
└── tests/
```

## Example Session

The transcript below shows an actual Claude Code conversation using this skill.

### Turn 1: User asks for a scan

```
User: Before I commit, can you check examples/patient_demo.py for any PII?
```

### Turn 2: Claude invokes the regex detector

Claude (internal):
- Reads `SKILL.md` to understand the skill's interface
- Runs `python3 detect.py --json examples/patient_demo.py`
- Parses JSON output

```
Bash output:
{
  "file": "examples/patient_demo.py",
  "total_issues": 13,
  "findings": [
    {"line": 10, "pattern": "CPF", "match": "123.456.789-09", ...},
    {"line": 11, "pattern": "EMAIL", "match": "maria.santos@example.com", ...},
    ...
  ]
}
```

### Turn 3: Claude reports findings to user

```
Claude: I scanned patient_demo.py and found 13 PII patterns:

- 2 CPF numbers (lines 10, 18)
- 4 email addresses (lines 11, 19, 30, 34)
- 2 Brazilian phone numbers (lines 12, 20)
- 2 dates of birth (lines 13, 21)
- 1 SSN (line 14)
- 1 credit card (line 22)
- 1 API key (line 33)

A few of these are inside test fixtures and a few look like real-looking
synthetic data. Want me to also run the semantic detector for names and
free-text PII the regex can't catch?
```

### Turn 4: User says yes

```
User: Yes, run the semantic scan too.
```

### Turn 5: Claude runs the LLM-based detector

Claude runs `python3 semantic_detector.py --json examples/patient_demo.py`:

```
Output: 2 additional findings:
- Line 9: NAME "Maria Santos"
- Line 17: NAME "João Silva"
```

### Turn 6: Claude reports the combined picture

```
Claude: The semantic scan caught 2 person names the regex missed:

- Maria Santos (line 9)
- João Silva (line 17)

These are full names attached to patient records, which counts as PII
under LGPD. Want me to clean the file using fix.py? It will replace each
finding with a synthetic equivalent that has the same format.
```

### Turn 7: User asks for the fix

```
User: Yes, but show me the diff first; I'll review before saving.
```

### Turn 8: Claude generates the cleaned file

Claude runs `python3 fix.py examples/patient_demo.py` (writes to `.cleaned`),
then `diff examples/patient_demo.py examples/patient_demo.py.cleaned`:

```
< "cpf": "123.456.789-09",
> "cpf": "960.013.389-14",
< "email": "maria.santos@example.com",
> "email": "synthetic2824@example.com",
< "phone": "(11) 98765-4321",
> "phone": "(39) 92286-2679",
...
```

### Turn 9: Claude offers to commit the cleaned version

```
Claude: The cleaned file has 13 replacements. The synthetic CPFs are
Luhn-valid so they still parse as CPFs in downstream code. The synthetic
emails use the example.com domain (reserved for documentation).

Want me to overwrite the original with the cleaned version, or save
patient_demo.py.cleaned as a separate file for your review?
```

### Turn 10: User decides

```
User: Save it as a separate file. I want to handle the names manually.
```

Claude leaves `examples/patient_demo.py.cleaned` in place. The user reviews
the names (Maria Santos, João Silva) and decides whether to replace those
manually (the LLM detector flagged them; the regex did not).

## Skill Integration Pattern

The skill demonstrates the recommended pattern for Claude Code skills:

1. **SKILL.md is the manifest**: describes what the skill does, when to use it, and how to invoke it
2. **Standalone CLI**: every capability has a CLI entry point that Claude can call via Bash
3. **JSON output mode**: Claude parses structured output, not free-form text
4. **Layered detection**: fast regex first, then optional LLM for semantic depth
5. **Reversible actions**: `fix.py` writes to a new file by default; `--in-place` is opt-in
6. **No silent mutations**: every change is reported, every fix is logged

## Why This Pattern Works

- **Composable**: Claude can chain `detect.py` → `semantic_detector.py` → `fix.py`
- **Auditable**: each step produces JSON that becomes part of the conversation context
- **User-controlled**: Claude reports findings and asks before applying fixes
- **Backend-agnostic**: works with or without LLM access (mock mode for testing)

## Pre-commit Hook Integration

For an even tighter integration, the skill can run as a pre-commit hook:

```bash
# .git/hooks/pre-commit
#!/bin/bash
for file in $(git diff --cached --name-only --diff-filter=ACM); do
    if [[ "$file" =~ \.(py|js|ts|md|txt|json|yaml|yml)$ ]]; then
        python3 .claude/skills/pii-detector/detect.py "$file" || {
            echo "PII detected in $file. Run 'fix.py $file' or remove manually before committing."
            exit 1
        }
    fi
done
```

This makes the skill a guardrail, not just a tool. Bad commits get blocked at the source.

## Limitations of This Integration

- Mock semantic findings only cover a few known files; production would call the LLM every time
- The skill cannot detect PII in binary files (images, PDFs, EHR exports)
- Names that are also common words (Hope, Faith, Grace) may be missed
- Live LLM calls cost tokens; for high-volume use, consider caching findings per file hash
