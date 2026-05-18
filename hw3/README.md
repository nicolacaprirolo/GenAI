## 🎥 Video Walkthrough

**[▶️ Watch on Loom (2 minutes)](PASTE_LOOM_LINK_HERE)**

Link: PASTE_LOOM_LINK_HERE

---

# HW3: ReAct Math Agent with Tool Use

A real multi-turn ReAct (Reasoning + Acting) agent following Yao et al. (2023). The agent solves math problems that require external data (product prices) by reasoning, calling tools, observing results, and iterating.

## Rubric Mapping

| Rubric requirement | File |
|--------------------|------|
| README | `README.md` (this file) |
| Agent entry point | `agent.py` (thin wrapper) and `math_agent.py` (core) |
| Tools documentation | `tools.md` (full schemas, return contracts, refusal behavior) |
| Evaluation set (≥8 cases) | `eval_set.json` (10 cases including 2 edge cases) |
| 1-2 page report | `report.md` (business case, baseline vs ReAct, deploy plan) |
| Evaluation methodology | `EVALUATION.md` (per-question results, baseline comparison) |
| Video walkthrough script | `VIDEO_SCRIPT.md` (talking notes for the recording) |

## One-Command Run

```bash
python3 agent.py            # live mode (requires Ollama at localhost:11434)
python3 agent.py --mock     # offline mode for grader reproducibility
python3 agent.py --no-tools # baseline: same model, no tool access (shows the lift)
```

## Headline Result

| Condition | Accuracy | Tool Calls |
|-----------|----------|------------|
| ReAct with tools (live, qwen3-coder) | **10/10 (100%)** | 19 |
| No-tool baseline (live, qwen3-coder) | 1/10 (10%) | 0 |
| ReAct mock mode (offline grading) | 10/10 (100%) | 18 |

The 90 percentage-point lift from adding tools demonstrates the central claim of the ReAct paper: external knowledge retrieval grounds the reasoning in facts, preventing hallucinated answers.

## Problem

Many calculations require external data (product prices, conversion rates, configuration values) that the language model cannot reliably produce from its parameters. A pure-LLM approach hallucinates plausible-looking numbers that are often wrong. A ReAct agent that can call tools fixes this.

## Solution

A multi-turn loop that interleaves four step types:
- **Thought**: agent reasons about what to do next
- **Action**: agent calls a tool with parameters
- **Observation**: agent receives the tool's response
- **Answer**: agent produces the final answer

Two tools are available:
- `product_lookup(product_name)`: get a product's price from the catalog
- `apply_discount(price, percent)`: compute a discounted price

The agent also handles edge cases by explicitly refusing:
- Unknown products: returns "REFUSAL" instead of guessing
- Ambiguous requests: returns "CLARIFY" instead of inventing details

## Files

```
hw3/
├── math_agent.py            # main script with ReAct loop + tools + baseline
├── README.md                # this file
├── EVALUATION.md            # detailed methodology and result analysis
├── VIDEO_SCRIPT.md          # 2-3 minute walkthrough script
├── requirements.txt
├── .gitignore
└── outputs/
    ├── agent_results_live.json     # ReAct loop with tools, live LLM
    ├── agent_results_no_tools.json # baseline without tools
    └── agent_results_mock.json     # offline grading mode
```

## Quickstart

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run with mock traces (no LLM required; for graders)
python3 math_agent.py --mock

# Run with real LLM + tools (requires Ollama)
python3 math_agent.py

# Run no-tool baseline to see hallucination rate
python3 math_agent.py --no-tools

# Run a single question
python3 math_agent.py --question q1
```

## Test Cases (10 total)

8 math questions + 2 edge cases:

| ID | Category | Question | Expected |
|----|----------|----------|----------|
| q1 | multi_product_sum | 2 laptops + 3 keyboards total | $2760 |
| q2 | budget_floor_div | Mice budget after 1 keyboard, $500 | 8 |
| q3 | discount | Headphones 20% off | $144 |
| q4 | budget_floor_div | Monitors for $1800 after 1 laptop | 5 |
| q5 | multi_product_sum | 2 headphones + 3 webcams + 1 lamp | $710 |
| q6 | multi_product_sum | 4 offices, chair + lamp each | $2060 |
| q7 | multi_product_sum | Bundle: 2 monitors + 1 kbd + 2 mice | $910 |
| q8 | discount_floor_div | Bulk webcams 15% off, $1000 | 12 |
| q9_edge_missing | edge_missing_product | Price of tablet (not in catalog) | REFUSAL |
| q10_edge_ambiguous | edge_ambiguous | "Buy some stuff" | CLARIFY |

## Backends

| Backend | When | How |
|---------|------|-----|
| Mock | Grader without LLM | `--mock` uses pre-recorded traces |
| Live + tools | Real ReAct demo | Default, Ollama at localhost:11434 |
| Live, no tools | Baseline | `--no-tools` shows hallucination rate |

## Implementation Notes

### Tool Call Format Handling

Different models output tool calls in different formats:
- OpenAI-standard models return structured `tool_calls` in the message
- Qwen variants on Ollama emit text-format calls like `<function=...><parameter=...>`

The agent handles both. If `msg.tool_calls` is populated, it processes those. Otherwise it parses text-format calls from the content using regex. This makes the implementation portable across model families.

### Multi-turn Loop

The loop runs up to 8 iterations. Each iteration:
1. Send messages + tool schema to model
2. If model returns tool calls, execute them, append results to messages, continue
3. If model returns a final answer, extract and return

This is the canonical ReAct multi-turn pattern. The loop terminates when the model decides it has enough information to answer.

### Answer Extraction

The extractor handles three signal types:
1. **Refusal signals**: "not_found", "refusal", "not in the catalog", etc., return "REFUSAL"
2. **Clarify signals**: "could you please specify", "what kind of", etc., return "CLARIFY"
3. **Numerical answers**: "Final answer: $2,060" (comma-tolerant), "$144", or final number in text

## Evaluation Results

### Live mode with tools: 10/10 correct
Every question produced the correct answer. The agent used product_lookup for price retrieval and apply_discount for percentage calculations. Edge cases were handled by explicit refusal rather than hallucination.

### Live mode without tools: 1/10 correct
Without tool access, the agent hallucinated product prices and got nearly every math problem wrong. The only correct case was q10 (ambiguous), which the agent appropriately asked to clarify regardless of tools.

This 90-point delta directly demonstrates the value proposition of ReAct: tool-augmented agents outperform reasoning-only agents on tasks that need external data.

## Limitations

- Tool catalog is small (8 products); production would point at a real database
- Floor division logic depends on the model interpreting "how many can I buy" correctly
- The agent does not currently cache repeated lookups within a session
- No retry logic on tool errors
- Single model tested (qwen3-coder via Ollama); other models may need different parsers
- Edge cases test only product-not-found and ambiguous request; production would need more (network failure, malformed input, etc.)

## Course Material Tie-In

- **Yao et al., 2023 (ReAct)**: The full Reasoning + Acting pattern is implemented here, not just discussed. The 90-point lift over the no-tool baseline replicates the paper's central finding that external tool use grounds language model reasoning.
- **Wei et al., 2023 (Chain-of-Thought)**: The agent produces intermediate reasoning steps before each tool call and before the final answer. This is CoT applied within the ReAct loop.
- **The AI Agent Handbook (Google)**: The implementation follows the recommended pattern of explicit tool schemas, message history accumulation, and refusal behavior for out-of-scope requests.
- **OWASP Top 10 for LLM Applications**: The refusal cases (q9, q10) demonstrate guard rails against prompt-injected fabrication. The agent does not invent prices for products not in the catalog.
