# HW3 Video Walkthrough Script (2-3 minutes)

Target length: 2:45. Talking notes for screen-recorded walkthrough.

## Setup before recording
- Terminal open in `hw3/` directory
- Ollama running with `qwen3-coder:latest` pulled
- Editor showing `math_agent.py` with tool definitions visible
- `outputs/` directory cleared

## Scene 1: The problem (0:00-0:25)

> "Math problems that depend on external data are a classic LLM failure mode. The model has to know prices, conversion rates, or inventory numbers it has no reliable way to produce. My HW3 implements a real ReAct agent that solves this by giving the model tools to look up the data it needs."

Show: open `math_agent.py` in editor, point to `MATH_QUESTIONS` and `TOOL_REGISTRY`.

## Scene 2: The architecture (0:25-0:55)

> "The agent follows the ReAct pattern from Yao 2023. It loops: think, call a tool, observe the result, repeat. Two tools are available: product_lookup for prices, and apply_discount for percentage calculations. There are also two edge cases, what happens when a product isn't in the catalog, and what happens when the request is ambiguous."

Show: scroll to the `run_react_loop` function, then to `TOOLS_SCHEMA`.

## Scene 3: Run live with tools (0:55-1:35)

> "Let me run all 10 questions through the live agent against qwen3-coder via Ollama."

Run:
```bash
python3 math_agent.py
```

Show: terminal output streaming. Point out:
- q1 calls product_lookup twice (laptop, keyboard) then computes
- q3 calls product_lookup then apply_discount (multi-tool orchestration)
- q9 calls product_lookup, gets NOT_FOUND, and refuses instead of guessing
- q10 doesn't call any tools and asks for clarification

End with the summary line: "10/10 correct."

## Scene 4: Run the baseline (1:35-2:05)

> "Now the interesting comparison. Same model, same questions, but I turn off tool access. The agent has to invent prices from training data."

Run:
```bash
python3 math_agent.py --no-tools
```

Show: terminal output. Point out the failures, every numerical question gets a wrong answer because the model hallucinates prices.

End with the summary line: "1/10 correct."

## Scene 5: The lift (2:05-2:30)

> "10% to 100% accuracy from a single architectural change. That's the ReAct paper's central claim, replicated here on a math task. Without tools, the model invents plausible-looking but wrong numbers. With tools, it looks them up. The difference isn't prompt engineering. It's giving the agent ground truth."

Show: open EVALUATION.md, point to the headline table.

## Scene 6: Edge cases matter (2:30-2:45)

> "One more thing, the agent refuses to make up answers. For q9 (tablet, not in catalog) and q10 (ambiguous request), it explicitly refuses instead of hallucinating. That refusal behavior is as important as the right answers. An agent that confidently invents data is more dangerous than one that admits ignorance."

Show: `outputs/agent_results_live.json` with the q9 and q10 traces visible.

## Live demo backup notes

If qwen3-coder is too slow on the recorder's machine, swap to devstral:latest. Tool calling works on both, just with different parsing paths (devstral uses native tool_calls; qwen uses text-format).

For grader reproducibility without Ollama:
```bash
python3 math_agent.py --mock
```
This uses pre-recorded traces and produces the same 10/10 score deterministically.

## Key talking points (use as needed)

- The agent uses 19 tool calls across 10 questions, about 2 per question, which matches the expected complexity
- The text-format tool call parser is real engineering work; demo code on GPT-4 hides this
- Refusal behavior is a feature, not a bug; tied to OWASP LLM Top 10 guardrails
- The whole thing runs offline on a local Ollama model; no cloud cost, no data leakage
