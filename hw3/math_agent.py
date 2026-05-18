#!/usr/bin/env python3
"""HW3 ReAct Math Agent with Tool Use.

Implements a real multi-turn ReAct loop (Yao et al., 2023) using an
OpenAI-compatible chat model with function/tool calling. The agent reasons,
calls tools, observes results, and iterates until it produces a final answer.

Backends:
- live: real LLM with tool calling (default, requires Ollama at localhost:11434)
- mock: pre-recorded traces for offline grading (--mock flag)

Two tools are available:
- product_lookup(product_name): get product price from catalog
- apply_discount(price, percent): compute discounted price

The agent also handles edge cases (missing products, ambiguous requests) by
explicitly refusing instead of hallucinating answers.
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()

DEFAULT_OLLAMA_URL = "http://localhost:11434/v1"
DEFAULT_MODEL = "qwen3-coder:latest"

PRODUCT_DATABASE = {
    "laptop": 1200,
    "mouse": 45,
    "keyboard": 120,
    "monitor": 350,
    "headphones": 180,
    "webcam": 95,
    "desk lamp": 65,
    "chair": 450,
}


def product_lookup(product_name: str) -> str:
    """Tool: look up product price."""
    key = product_name.lower().strip()
    if key in PRODUCT_DATABASE:
        return f"${PRODUCT_DATABASE[key]}"
    available = ", ".join(sorted(PRODUCT_DATABASE.keys()))
    return f"NOT_FOUND: product '{product_name}' is not in the catalog. Available products: {available}"


def apply_discount(price: float, percent: float) -> str:
    """Tool: apply percentage discount to a price."""
    if percent < 0 or percent > 100:
        return f"ERROR: discount percent must be between 0 and 100, got {percent}"
    discounted = price * (1 - percent / 100)
    return f"${discounted:.2f}"


TOOL_REGISTRY = {
    "product_lookup": product_lookup,
    "apply_discount": apply_discount,
}


TOOLS_SCHEMA = [
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
                        "description": "Name of the product to look up (e.g., 'laptop', 'mouse', 'keyboard')",
                    }
                },
                "required": ["product_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "apply_discount",
            "description": "Apply a percentage discount to a price. Returns the discounted price.",
            "parameters": {
                "type": "object",
                "properties": {
                    "price": {"type": "number", "description": "Original price in dollars"},
                    "percent": {"type": "number", "description": "Discount percentage (0-100)"},
                },
                "required": ["price", "percent"],
            },
        },
    },
]


MATH_QUESTIONS = [
    {
        "id": "q1",
        "question": "A store sells laptops and keyboards. If a customer buys 2 laptops and 3 keyboards, what is the total cost?",
        "expected_answer": 2760,
        "expected_tools": ["product_lookup", "product_lookup"],
        "category": "multi_product_sum",
    },
    {
        "id": "q2",
        "question": "A mouse and a keyboard are needed. If you have a budget of $500, how many mice can you buy with the remaining budget after buying one keyboard?",
        "expected_answer": 8,
        "expected_tools": ["product_lookup", "product_lookup"],
        "category": "budget_floor_div",
    },
    {
        "id": "q3",
        "question": "Headphones are on sale with 20% discount. What is the discounted price per unit?",
        "expected_answer": 144,
        "expected_tools": ["product_lookup", "apply_discount"],
        "category": "discount",
    },
    {
        "id": "q4",
        "question": "A customer buys 1 laptop and wants to fill the remaining budget of $1800 with monitors. How many monitors can they buy?",
        "expected_answer": 5,
        "expected_tools": ["product_lookup"],
        "category": "budget_floor_div",
    },
    {
        "id": "q5",
        "question": "What is the total cost of 2 headphones, 3 webcams, and 1 desk lamp?",
        "expected_answer": 710,
        "expected_tools": ["product_lookup", "product_lookup", "product_lookup"],
        "category": "multi_product_sum",
    },
    {
        "id": "q6",
        "question": "You need to buy furniture for 4 office spaces, each needing 1 chair and 1 desk lamp. What is the total cost?",
        "expected_answer": 2060,
        "expected_tools": ["product_lookup", "product_lookup"],
        "category": "multi_product_sum",
    },
    {
        "id": "q7",
        "question": "A bundle includes 2 monitors, 1 keyboard, and 2 mice. What is the bundle price?",
        "expected_answer": 910,
        "expected_tools": ["product_lookup", "product_lookup", "product_lookup"],
        "category": "multi_product_sum",
    },
    {
        "id": "q8",
        "question": "Webcams can be bought in bulk with 15% discount per unit. How many can you buy with $1000?",
        "expected_answer": 12,
        "expected_tools": ["product_lookup", "apply_discount"],
        "category": "discount_floor_div",
    },
    {
        "id": "q9_edge_missing",
        "question": "What is the price of a tablet?",
        "expected_answer": "REFUSAL",
        "expected_tools": ["product_lookup"],
        "category": "edge_missing_product",
        "expected_behavior": "Agent should call product_lookup, receive NOT_FOUND, and explain that tablets are not in the catalog instead of guessing.",
    },
    {
        "id": "q10_edge_ambiguous",
        "question": "I want to buy some stuff. What should I get?",
        "expected_answer": "CLARIFY",
        "expected_tools": [],
        "category": "edge_ambiguous",
        "expected_behavior": "Agent should ask for clarification instead of making up a recommendation.",
    },
]


SYSTEM_PROMPT_WITH_TOOLS = """You are a math problem solver agent following the ReAct pattern.

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
- Always put the final answer in the format "Final answer: N" at the end of your response"""


SYSTEM_PROMPT_NO_TOOLS = """You are a math problem solver agent.

For each problem, show your reasoning step by step and state the final numerical answer.

Important: you do NOT have access to a product catalog. You must answer based on your own knowledge of typical product prices.

Always put the final answer in the format "Final answer: N" at the end of your response."""


@dataclass
class ReActTrace:
    """A single ReAct interaction trace."""

    question_id: str
    question: str
    steps: list[dict[str, Any]] = field(default_factory=list)
    final_answer: str = ""
    tool_calls: list[str] = field(default_factory=list)
    error: str | None = None


MOCK_TRACES: dict[str, dict[str, Any]] = {
    "q1": {
        "steps": [
            {"type": "thought", "content": "I need prices for laptops and keyboards."},
            {"type": "tool_call", "name": "product_lookup", "args": {"product_name": "laptop"}, "result": "$1200"},
            {"type": "tool_call", "name": "product_lookup", "args": {"product_name": "keyboard"}, "result": "$120"},
            {"type": "thought", "content": "2 laptops at $1200 = $2400. 3 keyboards at $120 = $360. Total = $2760."},
        ],
        "final_answer": "Final answer: 2760",
        "tool_calls": ["product_lookup", "product_lookup"],
    },
    "q2": {
        "steps": [
            {"type": "thought", "content": "I need keyboard and mouse prices, then divide remaining budget."},
            {"type": "tool_call", "name": "product_lookup", "args": {"product_name": "keyboard"}, "result": "$120"},
            {"type": "tool_call", "name": "product_lookup", "args": {"product_name": "mouse"}, "result": "$45"},
            {"type": "thought", "content": "Budget remaining: 500 - 120 = 380. Mice: 380 / 45 = 8.44, floor to 8."},
        ],
        "final_answer": "Final answer: 8",
        "tool_calls": ["product_lookup", "product_lookup"],
    },
    "q3": {
        "steps": [
            {"type": "thought", "content": "I need headphone price, then apply 20% discount."},
            {"type": "tool_call", "name": "product_lookup", "args": {"product_name": "headphones"}, "result": "$180"},
            {"type": "tool_call", "name": "apply_discount", "args": {"price": 180, "percent": 20}, "result": "$144.00"},
        ],
        "final_answer": "Final answer: 144",
        "tool_calls": ["product_lookup", "apply_discount"],
    },
    "q4": {
        "steps": [
            {"type": "thought", "content": "I need monitor price, then divide $1800 by it."},
            {"type": "tool_call", "name": "product_lookup", "args": {"product_name": "monitor"}, "result": "$350"},
            {"type": "thought", "content": "1800 / 350 = 5.14, floor to 5."},
        ],
        "final_answer": "Final answer: 5",
        "tool_calls": ["product_lookup"],
    },
    "q5": {
        "steps": [
            {"type": "tool_call", "name": "product_lookup", "args": {"product_name": "headphones"}, "result": "$180"},
            {"type": "tool_call", "name": "product_lookup", "args": {"product_name": "webcam"}, "result": "$95"},
            {"type": "tool_call", "name": "product_lookup", "args": {"product_name": "desk lamp"}, "result": "$65"},
            {"type": "thought", "content": "2*180 + 3*95 + 65 = 360 + 285 + 65 = 710"},
        ],
        "final_answer": "Final answer: 710",
        "tool_calls": ["product_lookup", "product_lookup", "product_lookup"],
    },
    "q6": {
        "steps": [
            {"type": "tool_call", "name": "product_lookup", "args": {"product_name": "chair"}, "result": "$450"},
            {"type": "tool_call", "name": "product_lookup", "args": {"product_name": "desk lamp"}, "result": "$65"},
            {"type": "thought", "content": "Per office: 450+65 = 515. Four offices: 4*515 = 2060."},
        ],
        "final_answer": "Final answer: 2060",
        "tool_calls": ["product_lookup", "product_lookup"],
    },
    "q7": {
        "steps": [
            {"type": "tool_call", "name": "product_lookup", "args": {"product_name": "monitor"}, "result": "$350"},
            {"type": "tool_call", "name": "product_lookup", "args": {"product_name": "keyboard"}, "result": "$120"},
            {"type": "tool_call", "name": "product_lookup", "args": {"product_name": "mouse"}, "result": "$45"},
            {"type": "thought", "content": "2*350 + 120 + 2*45 = 700 + 120 + 90 = 910"},
        ],
        "final_answer": "Final answer: 910",
        "tool_calls": ["product_lookup", "product_lookup", "product_lookup"],
    },
    "q8": {
        "steps": [
            {"type": "tool_call", "name": "product_lookup", "args": {"product_name": "webcam"}, "result": "$95"},
            {"type": "tool_call", "name": "apply_discount", "args": {"price": 95, "percent": 15}, "result": "$80.75"},
            {"type": "thought", "content": "1000 / 80.75 = 12.38, floor to 12."},
        ],
        "final_answer": "Final answer: 12",
        "tool_calls": ["product_lookup", "apply_discount"],
    },
    "q9_edge_missing": {
        "steps": [
            {"type": "tool_call", "name": "product_lookup", "args": {"product_name": "tablet"}, "result": "NOT_FOUND: product 'tablet' is not in the catalog. Available products: chair, desk lamp, headphones, keyboard, laptop, monitor, mouse, webcam"},
            {"type": "thought", "content": "The tablet is not in the catalog. I should refuse to guess and inform the user."},
        ],
        "final_answer": "Tablets are not in our product catalog. Available products are: chair, desk lamp, headphones, keyboard, laptop, monitor, mouse, webcam. Please choose from these. Final answer: REFUSAL",
        "tool_calls": ["product_lookup"],
    },
    "q10_edge_ambiguous": {
        "steps": [
            {"type": "thought", "content": "The user did not specify what they want to buy, their budget, or their needs. I should ask for clarification rather than guess."},
        ],
        "final_answer": "I need more information to help. Could you tell me: (1) what kind of items you are looking for (e.g., office, computing, furniture), and (2) your budget? Then I can suggest options from our catalog. Final answer: CLARIFY",
        "tool_calls": [],
    },
}


def parse_text_tool_calls(text: str) -> list[dict[str, Any]]:
    """Parse text-format tool calls used by some Ollama models.

    Detects patterns like:
        <function=product_lookup>
        <parameter=product_name>laptop</parameter>
        </function>
    Returns list of {name, args} dicts.
    """
    calls = []
    pattern = r"<function=(\w+)>(.*?)</function>"
    for match in re.finditer(pattern, text, re.DOTALL):
        fn_name = match.group(1)
        params_text = match.group(2)
        args = {}
        for p_match in re.finditer(r"<parameter=(\w+)>\s*(.*?)\s*</parameter>", params_text, re.DOTALL):
            key = p_match.group(1)
            value = p_match.group(2).strip()
            try:
                value = json.loads(value)
            except (json.JSONDecodeError, ValueError):
                try:
                    value = float(value) if "." in value else int(value)
                except ValueError:
                    pass
            args[key] = value
        calls.append({"name": fn_name, "args": args})
    return calls


def run_react_loop(
    question: str,
    model: str,
    base_url: str,
    use_tools: bool = True,
    max_iterations: int = 8,
) -> ReActTrace:
    """Run a real multi-turn ReAct loop using OpenAI-compatible API.

    Handles both:
    - Native OpenAI tool_calls (standard models like GPT-4)
    - Text-format tool calls (Qwen, Llama variants on Ollama)
    """
    from openai import OpenAI

    client = OpenAI(base_url=base_url, api_key=os.getenv("LLM_API_KEY", "ollama"))
    trace = ReActTrace(question_id="", question=question)

    system = SYSTEM_PROMPT_WITH_TOOLS if use_tools else SYSTEM_PROMPT_NO_TOOLS
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system},
        {"role": "user", "content": question},
    ]

    for iteration in range(max_iterations):
        try:
            kwargs: dict[str, Any] = {
                "model": model,
                "messages": messages,
                "max_tokens": 600,
                "temperature": 0.0,
            }
            if use_tools:
                kwargs["tools"] = TOOLS_SCHEMA

            response = client.chat.completions.create(**kwargs)
            msg = response.choices[0].message
        except Exception as e:
            trace.error = f"API call failed: {e}"
            return trace

        native_calls = msg.tool_calls if use_tools else None
        text_calls = parse_text_tool_calls(msg.content or "") if use_tools else []

        if native_calls:
            if msg.content:
                trace.steps.append({"type": "thought", "content": msg.content})
            messages.append({
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                    }
                    for tc in native_calls
                ],
            })
            for tc in native_calls:
                fn_name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    args = {}
                result = execute_tool(fn_name, args)
                trace.tool_calls.append(fn_name)
                trace.steps.append({"type": "tool_call", "name": fn_name, "args": args, "result": result})
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
            continue

        if text_calls:
            content_without_calls = re.sub(r"<function=\w+>.*?</function>", "", msg.content or "", flags=re.DOTALL).strip()
            if content_without_calls:
                trace.steps.append({"type": "thought", "content": content_without_calls})

            tool_results = []
            for call in text_calls:
                result = execute_tool(call["name"], call["args"])
                trace.tool_calls.append(call["name"])
                trace.steps.append({"type": "tool_call", "name": call["name"], "args": call["args"], "result": result})
                tool_results.append(f"<function={call['name']}> returned: {result}")

            messages.append({"role": "assistant", "content": msg.content or ""})
            messages.append({"role": "user", "content": "Tool results:\n" + "\n".join(tool_results) + "\n\nContinue your reasoning and either call more tools or provide the Final answer."})
            continue

        trace.final_answer = msg.content or ""
        if msg.content:
            trace.steps.append({"type": "answer", "content": msg.content})
        break

    if not trace.final_answer and trace.steps:
        for step in reversed(trace.steps):
            if step.get("type") in ("thought", "answer"):
                trace.final_answer = step.get("content", "")
                break

    return trace


def execute_tool(name: str, args: dict[str, Any]) -> str:
    """Execute a tool by name and return its string result."""
    if name not in TOOL_REGISTRY:
        return f"ERROR: unknown tool {name}"
    try:
        return TOOL_REGISTRY[name](**args)
    except TypeError as e:
        return f"ERROR: bad arguments for {name}: {e}"
    except Exception as e:
        return f"ERROR: {e}"


def run_mock(question_id: str) -> ReActTrace:
    """Return pre-recorded trace for the given question."""
    data = MOCK_TRACES.get(question_id)
    if not data:
        return ReActTrace(question_id=question_id, question="", error="no mock data")
    trace = ReActTrace(question_id=question_id, question="")
    trace.steps = data["steps"]
    trace.final_answer = data["final_answer"]
    trace.tool_calls = data["tool_calls"]
    return trace


def extract_answer(text: str) -> Any:
    """Extract the final answer from agent response, handling multiple formats."""
    lower = text.lower()

    refusal_signals = ["not_found", "refusal", "not in the catalog", "not in our catalog", "cannot find", "no such product"]
    if any(sig in lower for sig in refusal_signals):
        return "REFUSAL"

    clarify_signals = ["could you please specify", "could you tell me", "i need more information", "could you clarify", "please clarify", "what kind of", "what would you like", "clarify"]
    if any(sig in lower for sig in clarify_signals):
        return "CLARIFY"

    final_match = re.search(r"Final answer:\s*\$?([0-9,]+(?:\.\d+)?|[A-Z_]+)", text, re.IGNORECASE)
    if final_match:
        value = final_match.group(1).replace(",", "")
        if value.upper() in ("REFUSAL", "CLARIFY", "NOT_FOUND"):
            return "REFUSAL" if value.upper() in ("REFUSAL", "NOT_FOUND") else "CLARIFY"
        try:
            num = float(value)
            return int(num) if num.is_integer() else num
        except ValueError:
            return value

    dollar_matches = re.findall(r"\$([0-9,]+(?:\.\d+)?)", text)
    if dollar_matches:
        cleaned = dollar_matches[-1].replace(",", "")
        try:
            num = float(cleaned)
            return int(num) if num.is_integer() else num
        except ValueError:
            pass

    numbers = re.findall(r"\b\d+(?:\.\d+)?\b", text)
    if numbers:
        return float(numbers[-1])
    return None


def evaluate_run(question: dict[str, Any], trace: ReActTrace) -> dict[str, Any]:
    """Compare trace against expected behavior."""
    expected = question["expected_answer"]
    extracted = extract_answer(trace.final_answer)

    if isinstance(expected, str):
        is_correct = isinstance(extracted, str) and extracted == expected
    elif extracted is None:
        is_correct = False
    else:
        try:
            is_correct = abs(float(extracted) - float(expected)) < 0.01
        except (TypeError, ValueError):
            is_correct = False

    expected_tools = question.get("expected_tools", [])
    tool_set_match = sorted(trace.tool_calls) == sorted(expected_tools)

    return {
        "is_correct": is_correct,
        "extracted": extracted,
        "expected": expected,
        "tool_calls_match": tool_set_match,
        "tool_calls_made": trace.tool_calls,
        "tool_calls_expected": expected_tools,
    }


def detect_backend(mock_flag: bool, base_url: str) -> tuple[str, str]:
    """Decide which backend to use."""
    if mock_flag:
        return ("mock", "Forced mock mode.")

    import urllib.request
    import urllib.error

    try:
        urllib.request.urlopen(base_url.replace("/v1", "/api/tags"), timeout=2)
        return ("live", f"Live ReAct loop against {base_url}.")
    except (urllib.error.URLError, OSError):
        return ("mock", "Ollama not reachable; using mock traces.")


def main():
    parser = argparse.ArgumentParser(description="ReAct math agent with tool use.")
    parser.add_argument("--mock", action="store_true", help="Force mock mode")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Model name for live mode")
    parser.add_argument("--base-url", default=DEFAULT_OLLAMA_URL, help="OpenAI-compatible base URL")
    parser.add_argument("--no-tools", action="store_true", help="Disable tools (baseline)")
    parser.add_argument("--question", help="Run only this question ID")
    parser.add_argument("--max-iter", type=int, default=6, help="Max ReAct iterations")
    args = parser.parse_args()

    mode, msg = detect_backend(args.mock, args.base_url)
    print(f"[mode] {msg}")
    if mode == "live":
        print(f"[model] {args.model}")
    print(f"[tools] {'ON' if not args.no_tools else 'OFF (baseline)'}")
    print()

    questions = [q for q in MATH_QUESTIONS if not args.question or q["id"] == args.question]

    results = []
    for q in questions:
        print(f"--- {q['id']}: {q['question'][:70]}{'...' if len(q['question']) > 70 else ''}")
        print(f"    expected: {q['expected_answer']}")

        if mode == "mock":
            trace = run_mock(q["id"])
            trace.question = q["question"]
            trace.question_id = q["id"]
        else:
            trace = run_react_loop(
                q["question"],
                args.model,
                args.base_url,
                use_tools=not args.no_tools,
                max_iterations=args.max_iter,
            )
            trace.question_id = q["id"]

        eval_result = evaluate_run(q, trace)
        print(f"    tools called: {trace.tool_calls}")
        print(f"    extracted: {eval_result['extracted']}")
        print(f"    {'CORRECT' if eval_result['is_correct'] else 'INCORRECT'}")
        if trace.error:
            print(f"    ERROR: {trace.error}")
        print()

        results.append({
            "question_id": q["id"],
            "question": q["question"],
            "category": q["category"],
            "expected_answer": q["expected_answer"],
            "expected_tools": q.get("expected_tools", []),
            "trace_steps": trace.steps,
            "final_answer": trace.final_answer,
            "evaluation": eval_result,
            "error": trace.error,
        })

    total = len(results)
    correct = sum(1 for r in results if r["evaluation"]["is_correct"])
    tools_match = sum(1 for r in results if r["evaluation"]["tool_calls_match"])
    total_tool_calls = sum(len(r["evaluation"]["tool_calls_made"]) for r in results)

    summary = {
        "total_questions": total,
        "correct": correct,
        "incorrect": total - correct,
        "accuracy_pct": round(100 * correct / total, 1) if total else 0,
        "tool_choice_match": tools_match,
        "total_tool_calls": total_tool_calls,
    }

    output_dir = Path(__file__).parent / "outputs"
    output_dir.mkdir(exist_ok=True)

    suffix = "no_tools" if args.no_tools else ("mock" if mode == "mock" else "live")
    output_file = output_dir / f"agent_results_{suffix}.json"

    with open(output_file, "w") as f:
        json.dump({
            "metadata": {
                "course": "BU.330.760.41 - Generative AI in Business",
                "assignment": "HW3 - Math Agent with Tool Use",
                "model_paradigm": "ReAct (Reasoning + Acting), Yao et al. 2023",
                "mode": mode,
                "model": args.model if mode == "live" else "mock",
                "tools_enabled": not args.no_tools,
            },
            "summary": summary,
            "results": results,
        }, f, indent=2)

    print("=" * 70)
    print(f"Summary: {correct}/{total} correct ({summary['accuracy_pct']}%)")
    print(f"Tool choice match: {tools_match}/{total}")
    print(f"Total tool calls made: {total_tool_calls}")
    print(f"Saved to {output_file}")


if __name__ == "__main__":
    main()
