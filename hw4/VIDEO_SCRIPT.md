# HW4 Video Script (~75 seconds)

Read at a natural pace. Hits every rubric item. Designed to fit comfortably in the 45-90 second window.

---

Hi, I'm Nico Caprirolo. This is my walkthrough for Homework 4, the Reusable AI Skill.

[Show the folder tree in your terminal or file explorer]

I built `pii-detector`, a skill that scans code, logs, and text for personally identifiable information. It lives under `.claude/skills/pii-detector/`, which is the standard skill structure. The SKILL.md has the name and description in the frontmatter, and the deterministic work happens in `scripts/detect.py`.

[Show SKILL.md briefly, point at the frontmatter]

The description tells an agent exactly when to use this skill: before commit, before sharing logs, or before pasting content into an LLM, for files that may contain Brazilian or US healthcare PII.

[Show detect.py, scroll to the Luhn and CPF validation functions]

The script is genuinely load-bearing here. Prose alone cannot do Luhn validation on credit card numbers or compute Brazilian CPF check digits with modulo-11 arithmetic. Those calculations need code.

[Switch to terminal]

Three test prompts as the rubric requires. First, a normal case: scan a patient demo file that has 13 PII items.

[Run: `python3 .claude/skills/pii-detector/scripts/detect.py examples/patient_demo.py`]

13 findings across 7 pattern types. Every CPF and credit card passed check-digit validation.

Second, an edge case: scan a narrative file with names and addresses that the regex cannot see. The semantic layer uses an LLM to catch them.

[Run: `python3 .claude/skills/pii-detector/scripts/semantic_detector.py --mock examples/patient_narrative.txt`]

Four findings: full patient name, street address, contextual identifier "the patient in room 304", and a minor's name with age.

Third, a cautious case where the skill should NOT flag false positives. This file has template strings like "000-00-0000" that look like SSNs but aren't real PII.

[Run: `python3 .claude/skills/pii-detector/scripts/detect.py examples/version_string_traps.py`]

Zero findings. The all-zeros filter catches these obvious templates.

[Run: `python3 tests/evaluate.py`]

Precision, recall, and F1 all hit 1.0 across the labeled dataset.

The skill is reusable because the entire `.claude/skills/pii-detector/` folder can be dropped into any project, and Claude Code will pick it up automatically. Thanks.

---

## Rubric Coverage

| Rubric requirement | Where hit in script |
|---------------------|---------------------|
| Creative narrow skill | Opening: PII detection for healthcare compliance |
| Script is load-bearing | Paragraph 4: Luhn + CPF mod-11 cannot be prompts |
| Strong name + description | Paragraph 2: SKILL.md frontmatter shown |
| Proper skill structure | Opening + closing: `.claude/skills/pii-detector/scripts/` |
| Meaningful Python script | detect.py demonstrated live |
| Skill used in agent | Closing: "reusable because Claude Code picks it up" |
| Test on 3 prompts (normal, edge, cautious) | Scenes 5, 6, 7 |

## Recording Setup

Before hitting record:
1. Open the terminal in the `hw4/` directory
2. Open Cursor with `SKILL.md` and `scripts/detect.py` in tabs
3. Have the terminal pre-sized large enough to show output clearly

## Style Compliance

- No em dashes
- No forbidden words (align, enable, enhance, robust, ensure, highlight)
- No "not X, but Y" patterns
- No paragraphs ending with a citation
