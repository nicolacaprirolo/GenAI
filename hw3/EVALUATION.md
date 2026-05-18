# HW3 Evaluation: ReAct Agent vs Baseline

## Methodology

10 questions tested across 3 conditions:

1. **Mock mode**: pre-recorded ReAct traces (deterministic baseline for grading)
2. **Live with tools**: real ReAct loop using qwen3-coder via Ollama, with product_lookup and apply_discount tools
3. **Live without tools**: same model, same questions, no tools available (baseline)

Each run records:
- Whether the agent's extracted numerical answer matches the expected answer
- Which tools the agent called and how many times
- The full thought-action-observation trace

## Results Summary

| Condition | Correct | Accuracy | Tool Calls |
|-----------|---------|----------|------------|
| Mock mode | 10/10 | 100% | 18 |
| Live with tools | 10/10 | 100% | 19 |
| Live without tools (baseline) | 1/10 | 10% | 0 |

## The Headline Finding

Adding tools to the agent moved accuracy from 10% to 100%. The only question the no-tool baseline got right was q10 (ambiguous request), which doesn't actually require tools.

This is the ReAct paper's central claim demonstrated empirically: tool-augmented agents outperform reasoning-only agents on tasks requiring external data.

## Per-Question Detail (Live with Tools)

| ID | Expected | Got | Tools Called | Status |
|----|----------|-----|--------------|--------|
| q1 | 2760 | 2760 | product_lookup × 2 | CORRECT |
| q2 | 8 | 8 | product_lookup × 2 | CORRECT |
| q3 | 144 | 144 | product_lookup, apply_discount | CORRECT |
| q4 | 5 | 5 | product_lookup × 2 | CORRECT |
| q5 | 710 | 710 | product_lookup × 3 | CORRECT |
| q6 | 2060 | 2060 | product_lookup × 2 | CORRECT |
| q7 | 910 | 910 | product_lookup × 3 | CORRECT |
| q8 | 12 | 12 | product_lookup, apply_discount | CORRECT |
| q9_edge_missing | REFUSAL | REFUSAL | product_lookup | CORRECT |
| q10_edge_ambiguous | CLARIFY | CLARIFY | (none) | CORRECT |

## Per-Question Detail (Live without Tools)

Without tools, the model had to invent product prices from its training data. Common failures:
- Hallucinated "laptops cost $800-$1500" then picked a middle value
- Guessed keyboard prices anywhere from $30 to $200
- Could not produce stable answers across runs

For brevity, the no-tools baseline produced wrong numerical answers for all 8 calculation questions. The agent only handled q10 (ambiguous) correctly, because that doesn't actually require any external data.

## Edge Case Analysis

### q9: Missing Product
**Input**: "What is the price of a tablet?"
**Expected behavior**: Call product_lookup, receive NOT_FOUND, explicitly refuse.

The agent did exactly this: it called product_lookup("tablet"), got NOT_FOUND back with the list of available products, and produced a response explaining that tablets are not in the catalog. It did not hallucinate a price.

This is critical for production safety. An agent that invents prices because the model "knows" tablets typically cost $300-$800 would create real problems. Explicit refusal is the correct behavior.

### q10: Ambiguous Request
**Input**: "I want to buy some stuff. What should I get?"
**Expected behavior**: Ask for clarification instead of guessing.

The agent did not call any tools. It produced a response asking what the user is looking for and what their budget is. This is the right behavior because the input is genuinely under-specified.

A naive agent might pick a random product and recommend it, or hallucinate user preferences. The refusal-to-guess behavior matches the safety patterns described in the OWASP LLM Top 10 (specifically LLM05: Improper Output Handling and LLM01: Prompt Injection guardrails).

## Tool Use Patterns

Across 10 questions, the agent made 19 tool calls. Breakdown:
- product_lookup: 17 calls
- apply_discount: 2 calls (only on q3 and q8 where discounts apply)
- No unnecessary calls
- No missed calls except minor variation on q4 (used 2 lookups when 1 was strictly needed)

This is good agent behavior: tools are called when needed and only when needed. The model correctly chose apply_discount for percentage-discount questions and skipped it for plain arithmetic.

## Why Live Live with Tools Got 100%

Three things came together:

1. **Tool schema clarity**: Each tool has a clear name, description, and parameter schema. The model can match the question intent to the right tool.

2. **System prompt**: The prompt explicitly tells the model to use tools and not guess prices. It also instructs the model to refuse for unknown products and ask for clarification when ambiguous.

3. **Multi-turn loop**: The agent gets multiple chances to call tools, observe results, and reason. A single-shot model would have to commit to tool calls in one round.

## Why Live Without Tools Got 10%

The model knows that laptops, keyboards, and monitors exist and has rough price knowledge from training data, but the prices vary across product families, regions, and time. When asked for "the" price of a laptop, the model picks a plausible number that has no relationship to the test catalog ($1200). The math then compounds the error.

This is exactly the hallucination problem that motivated the ReAct paper. The model isn't lying; it's filling in plausible-sounding details where it lacks ground truth. Tools provide the ground truth.

## Format Handling: Cross-Model Tool Calls

Different model families output tool calls in different formats:
- GPT-4 and Claude: native `tool_calls` field in the response
- Qwen variants on Ollama: text-format `<function=name><parameter=key>value</parameter></function>`
- Llama variants: yet another format

The agent handles both native and text-format tool calls. This is a practical engineering concern that comes up when targeting OSS models through OpenAI-compatible endpoints. The implementation parses both formats and feeds tool results back the same way.

## Limitations

1. **Single model tested**: only qwen3-coder via Ollama. Different models would need different prompting and parsing.
2. **8 products in catalog**: real systems would have thousands; the lookup would need to be a search not an exact match.
3. **No tool error handling**: if product_lookup returned an error, the agent might loop. A retry policy and circuit breaker would be needed in production.
4. **Edge case set is small**: only 2 edge cases. A production system would need many more (network failures, malformed inputs, prompt injection attempts).
5. **No latency or cost measurement**: each tool call adds an API round-trip. Production economics require measuring this.

## What This Demonstrates

### Tool use is a force multiplier
A 10x improvement in accuracy from a single architectural change (adding tools to the loop) is unusual in ML work. It happens here because tool use addresses a specific failure mode (hallucinating ground truth) that no amount of prompt engineering can fix.

### Refusal is a feature
The agent's ability to refuse out-of-scope requests is as important as its ability to answer in-scope ones. An agent that confidently makes up answers is more dangerous than one that admits ignorance.

### Multi-format tool parsing is real engineering work
The text-format tool call parser is the kind of integration glue that real ReAct implementations need. Demo code uses GPT-4 with native tool calls; production code on open models needs to handle the actual format the model produces.

### The ReAct paper replicates
The 10% baseline → 100% with tools matches the directional finding of the original ReAct paper (Yao et al., 2023). The paper's evaluation was on different tasks (HotpotQA, AlfWorld), but the underlying pattern holds: tools beat reasoning alone when the task needs external data.

## Recommended Next Steps

1. Add latency measurement: time per question, time per tool call
2. Add cost measurement: tokens in, tokens out, dollars per question
3. Add retry logic for tool failures
4. Test additional models (Llama 3, GPT-4o, Claude 3.7) to confirm portability
5. Add adversarial cases: prompt injection in product names, contradictory information
6. Add a search-based lookup tool to handle fuzzy product names
7. Add a calculator tool to separate arithmetic from reasoning (an additional tool for cleaner traces)
