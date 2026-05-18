# HW4 Teleprompter Script (~85 seconds)

Read at natural pace. Paste the body between the dashes into CuePrompter or your prompter app of choice. Every rubric item is hit explicitly.

---

Hi, I'm Nico Caprirolo. This is my walkthrough for Homework 4, the Reusable AI Skill.

[Type] find .claude -type f

I built `pii-detector`, a skill for scanning code and text for personally identifiable information. It lives at the standard path: `.claude/skills/pii-detector/`, with `SKILL.md` at the root and the three scripts inside `scripts/`.

[Type] head -5 .claude/skills/pii-detector/SKILL.md

The SKILL.md frontmatter has a clear name and a description tuned for agent discovery. The description tells an agent exactly when to use this skill: before commit, before sharing logs, or before pasting content into an LLM.

The deterministic script is genuinely load-bearing here. Prose alone cannot run Luhn validation on credit card numbers or compute Brazilian CPF check digits with modulo-11 arithmetic. The script does that part. The agent orchestrates.

Three test cases as the rubric requires. First, a normal case.

[Type] python3 .claude/skills/pii-detector/scripts/detect.py examples/patient_demo.py

13 PII findings across 7 pattern types. Every CPF and credit card passes its check-digit validation.

Second, an edge case where the LLM layer catches free-text PII the regex cannot see.

[Type] python3 .claude/skills/pii-detector/scripts/semantic_detector.py --mock examples/patient_narrative.txt

4 findings: full patient name, street address, the contextual identifier "the patient in room 304", and a minor's name with age.

Third, a cautious case. This file has template strings like "000-00-0000" that look like SSNs but are not real PII.

[Type] python3 .claude/skills/pii-detector/scripts/detect.py examples/version_string_traps.py

Zero findings. The all-zeros filter excludes obvious templates so we keep precision at 1.0.

[Type] python3 tests/evaluate.py

Precision, recall, and F1 all hit 1.0 across the four-file labeled dataset.

[Switch to the Claude Code window]

To prove the skill works in an agent, here's a fresh Claude Code session in the same project. When I ask Claude to scan a file for PII, it reads the SKILL.md, recognizes the request, and calls the script via Bash. The skill is reusable: drop the `.claude/skills/pii-detector/` folder into any project and Claude Code picks it up automatically.

Thanks.

---

## Rubric Coverage Map

| Rubric requirement | Where hit in script |
|---------------------|---------------------|
| Creative narrow skill | Opening paragraph |
| Script is load-bearing | Paragraph 4 (Luhn + CPF mod-11) |
| Strong name + description | Paragraphs 2 and 3 (frontmatter shown) |
| Proper skill structure | Paragraph 2 (folder layout) |
| Meaningful Python script | Paragraphs 5-7 (live runs) |
| Test on 3 prompts (normal, edge, cautious) | Paragraphs 5, 6, 7 |
| Skill used successfully in an agent | Paragraph 9 (Claude Code session) |

## Timing Notes

- Total target: 85 seconds at natural pace
- The 4 `python3` commands each take 1-3 seconds to run, so you can talk through them
- The Claude Code part adds about 15 seconds; if you skip it, total drops to 70 seconds (still within the 45-90 second cap)

## Recording Setup

1. Two terminal windows side by side:
   - LEFT: where you run the 6 demo commands
   - RIGHT: where Claude Code is already running (`claude` command)
2. Loom captures your full screen
3. Read the script smoothly; commands take a couple seconds to run so pause briefly while output appears

## Style Compliance

- No em dashes
- No forbidden words (align, enable, enhance, robust, ensure, highlight)
- No "not X, but Y" patterns
- No paragraphs ending with a citation
