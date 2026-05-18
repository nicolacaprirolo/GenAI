# HW3: Math Agent with Tool Use

Building a ReAct (Reasoning + Acting) agent that combines reasoning with tool invocation to solve multi-step math problems.

## Problem

Many real-world calculations require looking up external data (product prices, conversion rates, configuration values) before performing arithmetic. A language model alone cannot reliably retrieve such data and may hallucinate values. An agent that can call tools fixes this gap.

## Solution

A ReAct agent that:
1. Reads a math question
2. Reasons about what information it needs
3. Calls the `product_lookup` tool to retrieve product prices
4. Performs the calculation
5. Returns a step-by-step solution with the final answer

## Architecture

The agent implements the ReAct pattern from Yao et al. (2023). Each step is one of:
- **Thought**: agent reasons about what to do next
- **Action**: agent calls a tool with parameters
- **Observation**: agent receives the tool's response
- **Answer**: agent produces the final answer

This trace is auditable. Every tool call is logged with its inputs and outputs.

## Tool

### product_lookup

Retrieves the price of a product from the product database.

Parameters:
- `product_name` (string): name of the product to look up

Available products:
- laptop: $1200
- mouse: $45
- keyboard: $120
- monitor: $350
- headphones: $180
- webcam: $95
- desk lamp: $65
- chair: $450

Returns: formatted price string or error if the product is not in the database.

## Test Cases

Eight math questions cover progressively complex reasoning:

| ID | Question Type | Tool Calls | Expected |
|----|--------------|------------|----------|
| q1 | Multi-product sum | 2 | $2760 |
| q2 | Budget remainder + floor division | 2 | 8 mice |
| q3 | Single product + discount | 1 | $144 |
| q4 | Budget allocation + floor division | 1 | 5 monitors |
| q5 | Three products combined | 3 | $710 |
| q6 | Per-unit cost x quantity | 2 | $2060 |
| q7 | Bundle pricing | 3 | $910 |
| q8 | Bulk discount + floor division | 1 | 12 webcams |

## Modes

Two execution modes:

**Mock Mode (default)**: Pre-recorded agent traces demonstrate the ReAct pattern without an API key. Each question has a deterministic solver showing the thought-action-observation sequence.

**Live Mode**: Uses the Anthropic API for actual agent reasoning. Set `AGENT_MODE=live` and provide `ANTHROPIC_API_KEY`.

## Usage

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Mock mode (no API key needed)
python3 math_agent.py

# Live mode (requires Anthropic API key)
export ANTHROPIC_API_KEY="your_key_here"
export AGENT_MODE=live
python3 math_agent.py
```

Output is saved to `outputs/agent_results.json` with the full trace, evaluation, and per-question details.

## Evaluation Methodology

Two metrics:
1. **Correctness**: extracted numerical answer matches expected answer
2. **Tool Usage**: number of tool calls made and which tools were used

The agent's final answer is parsed with a regex that extracts the last numerical value in the response. Answers are compared to expected values with a small tolerance.

## Results (Mock Mode)

- Total Questions: 8
- Correct: 8 (100%)
- Tool Calls: 15 across all questions
- Average tool calls per question: 1.9

The mock solver demonstrates the expected ReAct trace for each question. In live mode, accuracy depends on the model's reasoning ability and tool-use correctness.

## Key Findings

Tool-augmented agents are particularly valuable when:
- Data must come from authoritative sources (no hallucination)
- Calculations involve external lookup
- Step-by-step traceability matters
- Auditability is required for debugging or compliance

The ReAct pattern separates reasoning from action. This separation makes every step debuggable: if an answer is wrong, the trace shows whether the failure was in the reasoning, the tool call, or the post-tool calculation.

## Limitations

- Tool availability is pre-defined; agents cannot create new tools
- Tool descriptions must be precise for correct invocation by live models
- Answer extraction via regex is brittle (final number wins, see q8 example)
- Mock mode does not test the model's actual reasoning capability
- Live mode accuracy depends on the underlying model
- Floor division logic must be handled carefully; bulk discount must apply before division

## Course Reference

This implementation demonstrates the ReAct pattern from the Yao et al. (2023) paper, showing how language models can be augmented with tool use. The ReAct paper showed substantial improvements over chain-of-thought alone on HotpotQA and AlfWorld tasks because external knowledge retrieval grounds the reasoning in facts.

For this homework, the product database is small and deterministic. A real-world deployment would point `product_lookup` at a production database, an internal API, or a vector store, while keeping the same agent architecture.
