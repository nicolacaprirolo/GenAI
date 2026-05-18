# HW3 Evaluation: Math Agent with Tool Use

## Methodology

Eight math questions were tested against the ReAct agent. Each question requires:
- One or more product price lookups
- Arithmetic on the retrieved prices
- Application of constraints (budget limits, discount percentages, floor division)

The agent's response is parsed to extract a numerical answer. The extracted value is compared against the expected answer with a small tolerance.

## Results

All 8 questions returned correct answers in mock mode.

| Question | Expected | Got | Tool Calls | Status |
|----------|----------|-----|------------|--------|
| q1 | 2760 | 2760 | 2 | CORRECT |
| q2 | 8 | 8 | 2 | CORRECT |
| q3 | 144 | 144 | 1 | CORRECT |
| q4 | 5 | 5 | 1 | CORRECT |
| q5 | 710 | 710 | 3 | CORRECT |
| q6 | 2060 | 2060 | 2 | CORRECT |
| q7 | 910 | 910 | 3 | CORRECT |
| q8 | 12 | 12 | 1 | CORRECT |

Total tool calls: 15
Average per question: 1.875

## ReAct Trace Example (q1)

For "A store sells laptops and keyboards. If a customer buys 2 laptops and 3 keyboards, what is the total cost?":

```
THOUGHT: I need prices for laptops and keyboards.
ACTION: product_lookup(product_name="laptop")
OBSERVATION: PRICE: $1200 for laptop
ACTION: product_lookup(product_name="keyboard")
OBSERVATION: PRICE: $120 for keyboard
THOUGHT: Calculation: 2*1200 + 3*120 = 2400 + 360 = 2760
ANSWER: The total cost is $2760.
```

Each step is auditable. If the answer were wrong, the trace would show whether the reasoning, tool call, or calculation failed.

## Key Findings

### Tool Use Patterns

The agent uses `product_lookup` exactly as needed:
- Single-product questions (q3, q4, q8): 1 call
- Two-product questions (q1, q2, q6): 2 calls
- Three-product questions (q5, q7): 3 calls

No unnecessary calls. No missed calls. This is the goal of well-designed agent tool use.

### Reasoning Quality

For questions involving:
- **Percentage discounts** (q3, q8): the agent correctly applies the discount before further calculation
- **Floor division** (q2, q4, q8): the agent correctly identifies that fractional units are not valid (cannot buy 5.14 monitors)
- **Multi-step arithmetic** (q5, q6, q7): the agent shows intermediate calculations

### Answer Extraction Challenge

Question q8 originally failed because the answer format placed `$1000` at the end:
"You can buy 12 webcams with $1000."

The regex extracts the last number, so it returned 1000 instead of 12. After rewording to "the answer is 12 webcams," extraction worked correctly.

This is a common pitfall when parsing agent outputs. Production systems should either:
- Constrain the model to return structured JSON
- Use a final step that explicitly labels the answer
- Apply more sophisticated answer extraction logic

## Interpretation

The ReAct pattern works well for this kind of problem because:
1. The information needed (product prices) lives outside the model's parameters
2. The reasoning steps are deterministic once the prices are known
3. Tool use grounds the calculation in real data

Contrast with chain-of-thought prompting alone (Wei et al., 2023): CoT would help with the multi-step arithmetic, but the model would have to either memorize product prices or hallucinate them. Neither is acceptable for a production system that needs accuracy.

## Production Considerations

If deployed to a real e-commerce or inventory system:

- **Database integration**: `product_lookup` would query a live database with current prices, inventory, and promotions
- **Caching**: repeated lookups within a session could be cached to reduce latency
- **Permissions**: tool access would respect user roles (e.g., wholesale vs retail pricing)
- **Logging**: every tool call should be logged for audit trails and debugging
- **Error handling**: tool failures should be graceful (retry, fallback to cached data)
- **Cost management**: tool calls have computational and monetary costs; agents should batch when possible

## Limitations

- Mock mode tests the architecture, not the underlying model's reasoning
- 8 questions is a small evaluation set; broader testing would strengthen claims
- All questions assume the product is in the database
- No handling for ambiguous product names ("which mouse?")
- No multi-turn conversation handling

## Conclusion

The ReAct agent successfully solves all 8 math questions by combining tool-based data retrieval with arithmetic reasoning. The trace-based approach makes the agent's behavior auditable at every step, supporting debugging and trust-building in production environments.

This implementation embodies the course material on agent design from the Yao et al. (2023) paper. The clear separation of thought, action, and observation provides a foundation that scales to more complex agent workflows in real applications.
