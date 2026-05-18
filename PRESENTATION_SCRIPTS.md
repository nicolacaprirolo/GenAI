# Presentation Scripts: HW2, HW3, HW4

Read each script at a natural pace. Each runs about 2:30 to 3:00 minutes. Italics are stage directions for what to show on screen.

---

# HW2 Presentation Script: Clinical Brief Generator

**Total time: 2:45**

## Opening (0:00 to 0:25)

Hi, I'm Nico, founder of Holi Labs. We build clinical decision support for emerging markets. For Homework 2, I picked a problem I see every day in our partner hospitals: a primary care doctor in a public clinic in Brazil sees 40 patients per shift. They need a 30-second structured summary of each patient before the visit. A brief that looks confident but skips uncertainty is dangerous. A brief that's accurate but unstructured is unusable in the time available.

*Open `brief_generator.py` in the editor.*

## What I Built (0:25 to 1:00)

I built three prompt versions and tested them on five synthetic patient cases. Version 1 is the baseline, a single line asking the model to summarize. Version 2 forces a fixed format with five sections. Version 3 combines two course concepts: few-shot examples from the Brown 2020 paper, and chain-of-thought scaffolding from the Wei 2023 paper. V3 also reframes the model's role from documentation assistant to safety assistant.

*Scroll through the `PROMPTS` list and pause briefly on the V3 system prompt to show the two worked examples.*

## Live Demonstration (1:00 to 1:40)

Let me run the generator on all five cases in mock mode so anyone can reproduce this without an API key.

*Run `python3 brief_generator.py --mock` and let the output stream.*

Notice the heuristic score column. Version 2 actually beats Version 3 on most cases. That looks wrong, so I added a second evaluator: an LLM-as-judge that scores each brief on five clinical dimensions including uncertainty handling and safety posture.

*Run `python3 llm_judge.py --mock`.*

Now look at the spread. Version 1 averages 3.4 out of 10. Version 2 jumps to 7.2. Version 3 lands at 9.8. The ranking flipped because the heuristic was matching surface keywords, the judge was reading the actual clinical content.

## The Lesson (1:40 to 2:20)

This is the part I want to spend a minute on. The same five briefs produced opposite rankings depending on which evaluator I used. The heuristic was a regex that matched the literal word "ASSESSMENT" because that's the header Version 2 used. Version 3 used "CLINICIAN REVIEW REQUIRED" instead, and the regex missed it.

If I had shipped Version 1 based on a casual demo, the briefs would have looked fine on the easy cases. The problems show up under structured evaluation: missing-data blindness, no safety boundaries, no escalation language. The GenAI Divide paper says 95 percent of enterprise pilots fail to deliver ROI. Lack of rigorous evaluation is part of why.

*Open `ITERATION_LOG.md` and point to the V3 section.*

## Close (2:20 to 2:45)

Limitations: five synthetic cases is a small sample. The LLM-as-judge has its own biases. A real production version would need clinician validation on a held-out set, multi-judge agreement metrics, and adversarial cases with contradictory data. Code, evaluation results, iteration narrative, and the full prompt definitions are in the repo. Thanks.

---

# HW3 Presentation Script: ReAct Math Agent

**Total time: 2:45**

## Opening (0:00 to 0:25)

For Homework 3, I implemented a real ReAct agent following the Yao 2023 paper. The problem: math questions that depend on external data are a classic language model failure mode. The model has to know prices, conversion rates, or inventory numbers it has no reliable way to produce. Either it hallucinates plausible-looking values, or it fails. A tool-augmented agent fixes this.

*Open `math_agent.py` and point to the `TOOL_REGISTRY` block.*

## What I Built (0:25 to 0:55)

The agent has two tools. `product_lookup` returns the price of a product from a small catalog. `apply_discount` computes a discounted price. The agent loops: it reasons about what to do, calls a tool, observes the result, and iterates until it produces a final answer. There are also two edge cases in the test set. Question 9 asks about a tablet, which is not in the catalog. Question 10 is intentionally vague: "I want to buy some stuff, what should I get?". The agent should refuse both rather than make up answers.

*Show the `run_react_loop` function briefly, then scroll to `MATH_QUESTIONS`.*

## Live Demonstration with Tools (0:55 to 1:35)

Let me run all 10 questions through the live agent against Qwen3-Coder via local Ollama.

*Run `python3 math_agent.py` and wait for the stream.*

10 out of 10 correct. Notice the trace: for question 1, the agent called product_lookup twice, once for laptops, once for keyboards, then computed the total. For question 3, it called product_lookup, then apply_discount, demonstrating multi-tool orchestration. For question 9, the agent called product_lookup, got back NOT_FOUND, and explicitly refused to invent a price for the tablet. For question 10, it asked for clarification without calling any tools.

## The Baseline Comparison (1:35 to 2:10)

Now the interesting comparison. Same model, same questions, but I turn off tool access.

*Run `python3 math_agent.py --no-tools`.*

1 out of 10. Without tools, the model invents product prices from training data and the math compounds the error. The only correct answer is the ambiguous question, which doesn't actually need tools. That's a 90 percentage-point lift from a single architectural change: giving the agent ground truth.

*Open `EVALUATION.md` and point to the headline table.*

This replicates the ReAct paper's central finding on a different task. Tool use beats reasoning alone when the task needs external data.

## The Engineering Honesty (2:10 to 2:35)

One thing worth showing: Qwen3-Coder on Ollama outputs tool calls in a text format that the OpenAI compatibility layer doesn't translate. I built a parser that handles both native tool calls and the text format. This is the kind of integration glue real production code needs. Demo code on GPT-4 hides this work.

*Briefly show `parse_text_tool_calls` in the code.*

## Close (2:35 to 2:45)

The refusal behavior on questions 9 and 10 matters as much as the right answers on questions 1 through 8. An agent that confidently invents data is more dangerous than one that admits ignorance. That maps directly to the OWASP LLM Top 10 guardrails. Thanks.

---

# HW4 Presentation Script: PII Detector Skill

**Total time: 2:50**

## Opening (0:00 to 0:25)

For Homework 4, I built a Claude Code skill that I'll actually use in my day job. I work in healthtech, so LGPD and HIPAA compliance means PII can never end up in a commit, a log, or an LLM prompt. Commercial DLP tools target enterprise security teams. This skill targets the developer at the keyboard, scanning code before commit, before sharing logs, or before pasting context into an LLM.

*Open `SKILL.md` and show the metadata header.*

## What I Built (0:25 to 1:00)

The skill has three layers. Layer one, `detect.py`, is regex-based. It catches CPF, CNS, SSN, phones, emails, dates of birth, credit cards, and API keys. CPF and credit card matches are validated with check-digit logic so we don't flag random digits. Layer two, `semantic_detector.py`, is an LLM layer that catches names, addresses, and free-text health information the regex can't see. Layer three, `fix.py`, replaces every finding with a synthetic equivalent that preserves the format: Luhn-valid CPFs, example.com emails, 555-prefix phones.

*Run `ls -la` to show the file structure.*

## Live Demonstration of Layer 1 (1:00 to 1:35)

Let me start with the regex layer on a patient demo file that I seeded with PII for testing.

*Run `python3 detect.py examples/patient_demo.py`.*

13 findings across 7 pattern types. Each finding shows the line, pattern type, and matched text. Notice the CPFs and credit cards: the validators rejected anything that didn't pass check digits, so what you see here is real-format PII.

## Live Demonstration of Layer 2 (1:35 to 2:10)

Now the LLM layer on a narrative file. This is the kind of text the regex can't handle.

*Run `python3 semantic_detector.py --model devstral:latest examples/patient_narrative.txt`.*

Four findings the regex never could have caught. A full patient name. A street address with city and postal code. The phrase "the patient in room 304", which identifies a specific individual by location. And the daughter Ana, age 8, which is critical because that's a minor.

## Live Demonstration of Layer 3 (2:10 to 2:35)

Now the fix mode. It reads the regex findings and replaces every match with a synthetic equivalent.

*Run `python3 fix.py examples/patient_demo.py` then `diff examples/patient_demo.py examples/patient_demo.py.cleaned`.*

You can see the diff: synthetic CPFs that still parse as CPFs in downstream code, synthetic emails at example.com, synthetic phones. The replacements are deterministic with a fixed random seed so the same input produces the same output.

## The Evaluation (2:35 to 2:50)

I evaluated against a labeled ground-truth dataset using precision, recall, and F1. The dataset includes a negative test set: things that look like PII but aren't, like the string "000-00-0000" or "(000) 000-0000". After adding a small all-zeros filter, the detector hits 1.0 on all three metrics across 20 PII items and 4 files.

*Run `python3 tests/evaluate.py`.*

Honest caveat: 4 files is a small dataset. Production deployment would target around 0.95 F1 once you add adversarial cases. Code, integration transcript, and evaluation results are in the repo. Thanks.

---

# Universal Closing Notes

For all three presentations:

- Speak slowly enough that the terminal output is readable behind you
- If a live demo fails, switch to `--mock` mode and continue without comment
- The detailed READMEs and EVALUATION docs in each folder are the source of truth if the audience asks follow-up questions
- Source code is on the `main` branch of the Homework repo, with one commit per A-grade upgrade
