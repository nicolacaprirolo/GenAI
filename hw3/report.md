# HW3 Report: ReAct Math Agent with Tool Use

**Author**: Nicola Capriolo Teran
**Course**: BU.330.760.41, Generative AI in Business, Spring 2026
**Assignment**: HW3, Build a Math Agent with Tool Use

---

## 1. Business Case

Internal users at Holi Labs (operations, finance, customer success) frequently ask questions that mix natural language with structured data lookups. Common pattern: "If we add 200 clinicians next quarter, what's the additional cost given our current per-clinician pricing?" or "How many monitors fit in the office budget after we buy the new chairs?". Today these questions go to a human analyst because LLM chat alone hallucinates the pricing data.

An agent that can call a `product_lookup` tool against a real catalog (or a `pricing_tier` tool against Stripe, or `cost_per_user` against our internal billing system) fixes that. The model handles natural-language understanding and arithmetic. The tool handles ground-truth data retrieval. Together they produce answers that are both conversational and accurate.

The financial story is simple. Holi Labs has approximately 12 internal stakeholders who routinely ask these questions. If each saves 15 minutes per day (today they ping the analyst and wait), that is 3 hours daily recovered across the company. At fully-loaded analyst cost of approximately R$120 per hour, that is R$1,440 per business day, or roughly R$360k per year.

The risk story matters too. An agent that confidently hallucinates a $2,500 laptop price when our catalog says $1,200 would create budget mistakes downstream. Refusal behavior for out-of-scope requests is therefore a feature, not a bug.

## 2. Model Choice

For the implementation, I tested `qwen3-coder:latest` (Qwen2 family, ~7B parameters) running locally via Ollama. Qwen3-coder was chosen because it supports tool calling and runs quickly on commodity hardware. For production, the model selection would shift to Claude 3.7 Sonnet or GPT-4o for hosted reliability, but the agent architecture stays the same because the OpenAI-compatible endpoint pattern is portable.

One specific engineering choice: Qwen3-coder on Ollama outputs tool calls in a text format (`<function=name><parameter=key>value</parameter></function>`) rather than the OpenAI-standard `tool_calls` JSON field. The agent handles both formats. This kind of cross-model integration glue is real production work that demo code on GPT-4 hides.

## 3. Baseline vs Final

The headline experiment: same model, same 10 questions, only difference is whether tools are available.

### Results

| Condition | Correct | Accuracy | Tool Calls | What it shows |
|-----------|---------|----------|------------|---------------|
| Live + tools | 10/10 | 100% | 19 total | The full ReAct paradigm working as designed |
| Live, no tools | 1/10 | 10% | 0 | What happens when the model has to hallucinate prices |
| Mock | 10/10 | 100% | 18 total | Deterministic baseline for grader reproducibility |

### Per-question accuracy (live + tools)

| Question | Category | Tools called | Answer | Status |
|----------|----------|--------------|--------|--------|
| q1 | multi_product_sum | product_lookup x 2 | $2760 | CORRECT |
| q2 | budget_floor_div | product_lookup x 2 | 8 mice | CORRECT |
| q3 | discount | product_lookup, apply_discount | $144 | CORRECT |
| q4 | budget_floor_div | product_lookup x 2 | 5 monitors | CORRECT |
| q5 | multi_product_sum | product_lookup x 3 | $710 | CORRECT |
| q6 | multi_product_sum | product_lookup x 2 | $2060 | CORRECT |
| q7 | multi_product_sum | product_lookup x 3 | $910 | CORRECT |
| q8 | discount_floor_div | product_lookup, apply_discount | 12 webcams | CORRECT |
| q9_edge_missing | edge | product_lookup | REFUSAL | CORRECT |
| q10_edge_ambiguous | edge | (none) | CLARIFY | CORRECT |

### Why the baseline fails

Without tools, the model has to invent product prices from training data. It "knows" laptops cost roughly $800 to $1500 and might pick $1000 as a plausible value. Catalog says $1200, so the answer is wrong by hundreds of dollars on every multi-product question. The error compounds across multiplications.

This is the ReAct paper's central claim demonstrated empirically: tool-augmented agents outperform reasoning-only agents on tasks requiring external data. The 90-point delta is unusually large in ML work because tool use addresses a specific failure mode (hallucinating ground truth) that no prompt-engineering trick can fix.

### Why the agent's refusals matter

Questions q9 and q10 test that the agent refuses instead of fabricating answers. On q9 (tablet, not in catalog) the agent called `product_lookup`, received NOT_FOUND, and explicitly declined to invent a tablet price. On q10 (vague request "buy some stuff") the agent asked for clarification on product category and budget instead of recommending arbitrary items.

These refusal behaviors are tied to the OWASP LLM Top 10 guardrails. An agent that confidently fabricates pricing is more dangerous than one that admits ignorance.

## 4. Where It Still Fails

The 10/10 score is on a small evaluation set. Specific limits worth calling out:

- **Catalog size is 8 products.** Real systems have thousands. The `product_lookup` tool would need to be a search rather than an exact match, which introduces fuzzy matching errors and possibly multiple-result handling.
- **No tool failure handling.** If `product_lookup` returns an HTTP 500, the current agent has no retry policy. Production needs exponential backoff and a circuit breaker.
- **Single model tested.** Qwen3-coder via Ollama. Different model families produce different tool-call formats. The parser handles two formats but new families may need additional handling.
- **Floor division logic depends on the model.** The system prompt explicitly says "you cannot buy fractional units" to head off "you can buy 8.44 mice" answers. A more capable model might handle this without explicit instruction; a less capable one might fail.
- **Edge case set is small.** Only two edge cases (missing product, ambiguous request). Production agents face many more: prompt injection in product names, contradictory information, network failures, malformed inputs, expired catalog entries.
- **No latency or cost measurement.** Each tool call is an API round-trip. Production economics require measuring tokens-per-question and dollars-per-question to make caching and batching decisions.

## 5. Deploy Recommendation

I would deploy this to internal pilot with the following conditions:

1. **Internal users only, opt-in.** Roll out to 12 internal Holi Labs stakeholders first. Track which questions they ask and how often the agent refuses correctly. Do not expose to customers until pilot data shows acceptable accuracy.

2. **Add a calculator tool.** A separate `calculate(expression)` tool would offload arithmetic from the model entirely. The current agent does the math in its head, which works for two-step arithmetic but compounds error on longer chains.

3. **Replace product_lookup catalog with the actual database.** Currently the catalog is a Python dict. Production version points at our pricing database with proper access control.

4. **Add a `search_products` tool.** Users say "the new chair" or "ergonomic mouse". The current agent fails on partial matches. A separate search tool with fuzzy matching would handle this.

5. **Tool call audit log.** Every tool invocation logged with timestamp, args, result, downstream usage, and final answer. This is the data we need to debug failures and detect prompt injection attempts.

6. **Per-tool rate limits.** A misbehaving agent could call `product_lookup` in a loop. Production needs per-tool quotas (e.g., max 20 calls per question) and per-user daily limits.

7. **Refusal monitoring.** Track when the agent refuses (q9-style) and when it asks for clarification (q10-style). Both should be common; if refusals drop to zero, the agent is probably hallucinating.

8. **Do not skip the human review step.** For any agent answer that triggers a downstream action (e.g., placing an order, updating a budget), require human confirmation. The agent assists, the human decides.

### Estimated Pilot Cost (4 weeks)

- 12 internal users x 5 questions per day x 20 working days = 1,200 questions
- Average ~3 tool calls per question, ~1500 tokens prompt + completion per call
- Total LLM cost at hosted API pricing (~$3/1M tokens): under $20 for the pilot
- Plus tooling integration cost (one engineer week): ~$3,000

The cost is trivial compared to the ~R$360k annual analyst-time recovery if the pilot validates. Risk is upside: we either confirm the value or learn fast what is missing.

## 6. Summary

The ReAct agent reaches 100% accuracy on 10 test questions when given two tools. Removing the tools drops accuracy to 10%. The 90-point delta replicates the ReAct paper's central finding on a new task and a different model family.

The two edge cases (refusal for unknown product, clarification for ambiguous request) demonstrate that the agent refuses to hallucinate when the right call is to admit ignorance. This refusal behavior is a production requirement, not a nice-to-have.

Deployment is recommended as a 4-week internal pilot with the conditions above. The biggest production additions would be: a real database backing `product_lookup`, a calculator tool to offload arithmetic, audit logging on every tool call, and human review on any agent answer that triggers downstream actions.

The course-material takeaway: the ReAct pattern is not just an academic result. It is the right architecture whenever a language model needs to act on data that lives outside its parameters. Tool use is the bridge between conversational interfaces and trustworthy answers.

---

**Repo**: github.com/nicolacaprirolo/GenAI/tree/main/hw3
**Demo video**: [link to be added after recording]
**Last updated**: 2026-05-18
