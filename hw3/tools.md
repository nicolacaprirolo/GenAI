# HW3 Tools

The ReAct agent has access to two tools. Each tool has a clear name, description, parameter schema, and return contract. Tools are registered in `math_agent.py:TOOL_REGISTRY` and exposed to the LLM via `TOOLS_SCHEMA` in standard OpenAI function-calling format.

---

## Tool 1: `product_lookup`

### Purpose
Retrieve the current price of a product from the catalog. The agent uses this when a question references a product whose price it does not know.

### Schema (OpenAI function format)

```json
{
  "type": "function",
  "function": {
    "name": "product_lookup",
    "description": "Look up the current price of a product in the catalog. Returns the price as a dollar amount, or NOT_FOUND with available products if the product is not in the catalog.",
    "parameters": {
      "type": "object",
      "properties": {
        "product_name": {
          "type": "string",
          "description": "Name of the product to look up (e.g., 'laptop', 'mouse', 'keyboard')"
        }
      },
      "required": ["product_name"]
    }
  }
}
```

### Catalog (8 products)

| Product | Price |
|---------|-------|
| laptop | $1200 |
| mouse | $45 |
| keyboard | $120 |
| monitor | $350 |
| headphones | $180 |
| webcam | $95 |
| desk lamp | $65 |
| chair | $450 |

### Return Contract

- **Match found**: `"$1200"` (dollar-prefixed price string)
- **Match not found**: `"NOT_FOUND: product 'X' is not in the catalog. Available products: chair, desk lamp, ..."`

The NOT_FOUND payload includes the full available product list so the agent can either refuse the request or propose alternatives.

### Why It Matters

Without this tool, the model must invent product prices from training data. As the baseline run demonstrates (`agent_results_no_tools.json`), invented prices produce wrong answers on 9 of 10 questions. The tool grounds every price retrieval in catalog truth.

---

## Tool 2: `apply_discount`

### Purpose
Compute a discounted price. Used for percentage-discount questions (q3, q8) where the model would otherwise have to do the arithmetic itself and risk error compounding.

### Schema

```json
{
  "type": "function",
  "function": {
    "name": "apply_discount",
    "description": "Apply a percentage discount to a price. Returns the discounted price.",
    "parameters": {
      "type": "object",
      "properties": {
        "price": {
          "type": "number",
          "description": "Original price in dollars"
        },
        "percent": {
          "type": "number",
          "description": "Discount percentage (0-100)"
        }
      },
      "required": ["price", "percent"]
    }
  }
}
```

### Return Contract

- **Valid percent (0-100)**: `"$144.00"` (dollar-prefixed, two decimal places)
- **Invalid percent**: `"ERROR: discount percent must be between 0 and 100, got X"`

### Why It Matters

This tool demonstrates multi-tool orchestration. On q3 ("headphones at 20% off"), the agent must call `product_lookup` first to get the original price, then `apply_discount` with the retrieved price and the discount percentage. The trace shows two distinct tool calls in sequence, which is the canonical multi-step ReAct pattern.

---

## Tool Call Format Handling

Different model families output tool calls differently:

| Model family | Format | Where parsed |
|--------------|--------|--------------|
| GPT-4, Claude, Llama 3.1+ | Native `tool_calls` field | `math_agent.py:run_react_loop` line ~365 |
| Qwen variants on Ollama | Text-format `<function=name><parameter=key>value</parameter></function>` | `math_agent.py:parse_text_tool_calls` line ~316 |

The agent handles both. If the response has a populated `tool_calls` array, it processes those. Otherwise it parses text-format calls from the content using regex. This makes the implementation portable across model families without changing the agent loop.

---

## Refusal Behavior

Two edge cases test that the agent refuses instead of inventing data:

| Question | Expected Behavior |
|----------|-------------------|
| q9: "What is the price of a tablet?" | Call `product_lookup("tablet")`, receive NOT_FOUND, explicitly refuse with the available products list |
| q10: "I want to buy some stuff. What should I get?" | Do not call any tool; ask for clarification on what kind of items and what budget |

These behaviors map to the OWASP LLM Top 10 guardrails (specifically LLM01: Prompt Injection and LLM06: Sensitive Information Disclosure). An agent that confidently invents prices is more dangerous than one that admits ignorance.

---

## System Prompt That Drives Tool Use

```
You are a math problem solver agent following the ReAct pattern.

You have access to two tools:
1. product_lookup(product_name): get the price of a product
2. apply_discount(price, percent): compute a discounted price

For each problem:
- Think about what information you need
- Call tools to get that information (do not guess prices)
- Show your arithmetic step by step
- State the final numerical answer clearly at the end

Important behaviors:
- If a product is not in the catalog (NOT_FOUND), say so and refuse to guess
- If the question is ambiguous or under-specified, ask for clarification rather than inventing details
- For "how many X can I buy with $Y" questions, use floor division (you cannot buy fractional units)
- Always put the final answer in the format "Final answer: N" at the end of your response
```

Key design choices in the prompt:
- Explicit "do not guess prices" instruction prevents hallucination even when the model "knows" approximate prices
- "Final answer: N" format makes answer extraction reliable across model outputs
- Floor division instruction prevents "you can buy 8.44 mice" answers on budget questions
- Refusal guidance is opt-in by case, so the model only refuses when the input warrants it

---

## What I Would Add for Production

1. **Caching layer**: same product lookups within a session should be cached
2. **Tool failure retries**: if a tool returns an error, the agent should retry once before giving up
3. **Latency budget**: cap tool calls per question (currently 8); enforce timeouts
4. **Tool versioning**: pin tool schemas to a version so old agents do not break on schema changes
5. **Audit log**: persist every tool call with timestamp, args, result, and downstream usage
6. **Per-tool permissions**: tools that mutate state (write_order, refund) need scoped access tokens
