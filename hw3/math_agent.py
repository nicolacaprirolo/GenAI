#!/usr/bin/env python3
"""HW3 Math Agent with Tool Use.

Demonstrates the ReAct (Reasoning + Acting) pattern from Yao et al. (2023).
The agent reasons through multi-step math problems and calls the product_lookup
tool when external data is needed.

Two modes:
- Live mode: uses Anthropic API for real agent reasoning (requires ANTHROPIC_API_KEY)
- Mock mode: uses pre-recorded agent traces for offline demonstration
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Callable

from dotenv import load_dotenv

load_dotenv()


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
    """Look up the price of a product. The agent's only available tool."""
    product_key = product_name.lower().strip()
    if product_key in PRODUCT_DATABASE:
        price = PRODUCT_DATABASE[product_key]
        return f"PRICE: ${price} for {product_name}"
    available = ", ".join(PRODUCT_DATABASE.keys())
    return f"ERROR: Product '{product_name}' not found. Available: {available}"


TOOLS = {
    "product_lookup": {
        "function": product_lookup,
        "description": "Look up the price of a product in the catalog.",
        "parameters": {"product_name": "string - name of the product"},
    },
}


MATH_QUESTIONS = [
    {
        "id": "q1",
        "question": "A store sells laptops and keyboards. If a customer buys 2 laptops and 3 keyboards, what is the total cost?",
        "expected_answer": 2760,
        "reasoning_path": ["lookup laptop", "lookup keyboard", "calculate: 2*1200 + 3*120 = 2400 + 360 = 2760"],
    },
    {
        "id": "q2",
        "question": "A mouse and a keyboard are needed. If you have a budget of $500, how many mice can you buy with the remaining budget after buying one keyboard?",
        "expected_answer": 8,
        "reasoning_path": ["lookup keyboard", "lookup mouse", "calculate: (500-120)/45 = 380/45 = 8.44, so 8 mice"],
    },
    {
        "id": "q3",
        "question": "Headphones are on sale with 20% discount. What is the discounted price per unit?",
        "expected_answer": 144,
        "reasoning_path": ["lookup headphones", "calculate: 180 * 0.8 = 144"],
    },
    {
        "id": "q4",
        "question": "A customer buys 1 laptop and wants to fill the remaining budget of $1800 with monitors. How many monitors can they buy?",
        "expected_answer": 5,
        "reasoning_path": ["lookup monitor", "calculate: 1800/350 = 5.14, so 5 monitors"],
    },
    {
        "id": "q5",
        "question": "What is the total cost of 2 headphones, 3 webcams, and 1 desk lamp?",
        "expected_answer": 710,
        "reasoning_path": ["lookup headphones", "lookup webcam", "lookup desk lamp", "calculate: 2*180 + 3*95 + 65 = 360 + 285 + 65 = 710"],
    },
    {
        "id": "q6",
        "question": "You need to buy furniture for 4 office spaces, each needing 1 chair and 1 desk lamp. What is the total cost?",
        "expected_answer": 2060,
        "reasoning_path": ["lookup chair", "lookup desk lamp", "calculate: 4 * (450 + 65) = 4 * 515 = 2060"],
    },
    {
        "id": "q7",
        "question": "A bundle includes: 2 monitors, 1 keyboard, and 2 mice. What is the bundle price?",
        "expected_answer": 910,
        "reasoning_path": ["lookup monitor", "lookup keyboard", "lookup mouse", "calculate: 2*350 + 120 + 2*45 = 700 + 120 + 90 = 910"],
    },
    {
        "id": "q8",
        "question": "Webcams can be bought in bulk with 15% discount. How many can you buy with $1000?",
        "expected_answer": 12,
        "reasoning_path": ["lookup webcam", "calculate: 95*0.85 = 80.75 discount price; 1000/80.75 = 12.38, so 12 webcams"],
    },
]


class ReActAgent:
    """Simple ReAct agent that interleaves thought, action, and observation."""

    def __init__(self, tools: dict[str, Any], mock_mode: bool = True):
        self.tools = tools
        self.mock_mode = mock_mode
        self.trace: list[dict[str, Any]] = []

    def think(self, thought: str) -> None:
        """Record a reasoning step."""
        self.trace.append({"type": "thought", "content": thought})

    def act(self, tool_name: str, tool_input: dict[str, Any]) -> str:
        """Execute a tool and record the observation."""
        self.trace.append({"type": "action", "tool": tool_name, "input": tool_input})
        if tool_name not in self.tools:
            observation = f"ERROR: Tool '{tool_name}' not available"
        else:
            tool_fn = self.tools[tool_name]["function"]
            try:
                observation = tool_fn(**tool_input)
            except Exception as e:
                observation = f"ERROR: {str(e)}"
        self.trace.append({"type": "observation", "content": observation})
        return observation

    def answer(self, final_answer: str) -> str:
        """Record the final answer."""
        self.trace.append({"type": "answer", "content": final_answer})
        return final_answer

    def solve(self, question_data: dict[str, Any]) -> dict[str, Any]:
        """Solve a math question using ReAct pattern."""
        self.trace = []
        question = question_data["question"]

        self.think(f"Question: {question}")

        if self.mock_mode:
            return self._solve_mock(question_data)
        return self._solve_live(question_data)

    def _solve_mock(self, question_data: dict[str, Any]) -> dict[str, Any]:
        """Mock solver that follows the pre-recorded reasoning path."""
        question_id = question_data["id"]
        expected = question_data["expected_answer"]

        mock_solutions = {
            "q1": self._solve_q1,
            "q2": self._solve_q2,
            "q3": self._solve_q3,
            "q4": self._solve_q4,
            "q5": self._solve_q5,
            "q6": self._solve_q6,
            "q7": self._solve_q7,
            "q8": self._solve_q8,
        }

        solver = mock_solutions.get(question_id)
        if solver is None:
            return {"answer": "Unknown", "trace": self.trace, "expected": expected}

        answer = solver()
        return {
            "answer": answer,
            "extracted_number": self._extract_number(answer),
            "expected": expected,
            "trace": self.trace,
            "tools_called": [step["tool"] for step in self.trace if step["type"] == "action"],
        }

    def _solve_live(self, question_data: dict[str, Any]) -> dict[str, Any]:
        """Live solver using Anthropic API (requires API key)."""
        try:
            import anthropic

            client = anthropic.Anthropic()
            messages = [
                {
                    "role": "user",
                    "content": f"Solve this math problem step by step. Use the product_lookup tool to get product prices.\n\nProblem: {question_data['question']}",
                }
            ]

            tools = [
                {
                    "name": "product_lookup",
                    "description": "Look up the price of a product",
                    "input_schema": {
                        "type": "object",
                        "properties": {"product_name": {"type": "string"}},
                        "required": ["product_name"],
                    },
                }
            ]

            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1024,
                tools=tools,
                messages=messages,
            )

            answer = ""
            for block in response.content:
                if hasattr(block, "text"):
                    answer += block.text

            return {
                "answer": answer,
                "extracted_number": self._extract_number(answer),
                "expected": question_data["expected_answer"],
                "trace": self.trace,
                "tools_called": [],
            }
        except Exception as e:
            return {
                "answer": f"Live mode failed: {e}",
                "expected": question_data["expected_answer"],
                "trace": self.trace,
                "tools_called": [],
            }

    def _solve_q1(self) -> str:
        self.think("I need prices for laptops and keyboards.")
        laptop_obs = self.act("product_lookup", {"product_name": "laptop"})
        keyboard_obs = self.act("product_lookup", {"product_name": "keyboard"})
        self.think("Calculation: 2*1200 + 3*120 = 2400 + 360 = 2760")
        return self.answer("The total cost is $2760.")

    def _solve_q2(self) -> str:
        self.think("I need prices for keyboard and mouse, then divide remaining budget.")
        self.act("product_lookup", {"product_name": "keyboard"})
        self.act("product_lookup", {"product_name": "mouse"})
        self.think("Calculation: (500 - 120) / 45 = 380 / 45 = 8.44. Floor to 8 mice.")
        return self.answer("You can buy 8 mice with the remaining budget.")

    def _solve_q3(self) -> str:
        self.think("I need headphone price, then apply 20% discount.")
        self.act("product_lookup", {"product_name": "headphones"})
        self.think("Calculation: 180 * (1 - 0.20) = 180 * 0.80 = 144")
        return self.answer("The discounted price is $144 per unit.")

    def _solve_q4(self) -> str:
        self.think("I need monitor price, then divide budget by it.")
        self.act("product_lookup", {"product_name": "monitor"})
        self.think("Calculation: 1800 / 350 = 5.14. Floor to 5 monitors.")
        return self.answer("They can buy 5 monitors.")

    def _solve_q5(self) -> str:
        self.think("I need prices for headphones, webcam, and desk lamp.")
        self.act("product_lookup", {"product_name": "headphones"})
        self.act("product_lookup", {"product_name": "webcam"})
        self.act("product_lookup", {"product_name": "desk lamp"})
        self.think("Calculation: 2*180 + 3*95 + 1*65 = 360 + 285 + 65 = 710")
        return self.answer("The total cost is $710.")

    def _solve_q6(self) -> str:
        self.think("I need chair and desk lamp prices, multiply by 4 offices.")
        self.act("product_lookup", {"product_name": "chair"})
        self.act("product_lookup", {"product_name": "desk lamp"})
        self.think("Calculation: 4 * (450 + 65) = 4 * 515 = 2060")
        return self.answer("The total cost for 4 office spaces is $2060.")

    def _solve_q7(self) -> str:
        self.think("I need monitor, keyboard, and mouse prices for the bundle.")
        self.act("product_lookup", {"product_name": "monitor"})
        self.act("product_lookup", {"product_name": "keyboard"})
        self.act("product_lookup", {"product_name": "mouse"})
        self.think("Calculation: 2*350 + 1*120 + 2*45 = 700 + 120 + 90 = 910")
        return self.answer("The bundle price is $910.")

    def _solve_q8(self) -> str:
        self.think("I need webcam price, apply 15% discount, then divide budget.")
        self.act("product_lookup", {"product_name": "webcam"})
        self.think("Calculation: 95 * 0.85 = 80.75 discounted price. 1000 / 80.75 = 12.38. Floor to 12.")
        return self.answer("With a $1000 budget, the answer is 12 webcams.")

    def _extract_number(self, text: str) -> float | None:
        """Extract the final numerical answer from agent response."""
        numbers = re.findall(r"\$?(\d+(?:\.\d+)?)", text)
        if numbers:
            return float(numbers[-1])
        return None


def evaluate_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Evaluate agent answers against expected values."""
    correct = 0
    tool_call_count = 0
    tool_usage: dict[str, int] = {}

    for result in results:
        extracted = result.get("extracted_number")
        expected = result.get("expected")
        if extracted is not None and abs(extracted - expected) < 0.01:
            correct += 1

        for tool in result.get("tools_called", []):
            tool_usage[tool] = tool_usage.get(tool, 0) + 1
            tool_call_count += 1

    return {
        "total": len(results),
        "correct": correct,
        "incorrect": len(results) - correct,
        "accuracy_pct": round(100 * correct / len(results), 1) if results else 0,
        "total_tool_calls": tool_call_count,
        "tool_usage": tool_usage,
    }


def format_report(results: list[dict[str, Any]], evaluation: dict[str, Any]) -> str:
    """Format evaluation report."""
    lines = [
        "",
        "Math Agent Evaluation Report",
        "=" * 70,
        "",
        f"Performance:",
        f"  Total Questions: {evaluation['total']}",
        f"  Correct: {evaluation['correct']} ({evaluation['accuracy_pct']}%)",
        f"  Incorrect: {evaluation['incorrect']}",
        "",
        f"Tool Usage:",
        f"  Total Tool Calls: {evaluation['total_tool_calls']}",
        f"  Tools Used: {evaluation['tool_usage']}",
        "",
        "Per-Question Details:",
        "-" * 70,
    ]

    for result in results:
        question_id = result.get("question_id", "?")
        status = "CORRECT" if result.get("is_correct") else "INCORRECT"
        marker = "✓" if result.get("is_correct") else "✗"
        lines.extend(
            [
                "",
                f"{marker} {question_id}: {status}",
                f"  Expected: {result['expected']}",
                f"  Got: {result['extracted_number']}",
                f"  Tools called: {result['tools_called']}",
            ]
        )

    return "\n".join(lines)


def main():
    """Run all 8 math questions through the agent."""
    mode = os.getenv("AGENT_MODE", "mock")
    print(f"Math Agent (mode: {mode})")
    print("=" * 70)

    agent = ReActAgent(tools=TOOLS, mock_mode=(mode == "mock"))
    results = []

    for question_data in MATH_QUESTIONS:
        print(f"\n{question_data['id']}: {question_data['question']}")
        print(f"  Expected: {question_data['expected_answer']}")

        result = agent.solve(question_data)
        extracted = result.get("extracted_number")
        is_correct = extracted is not None and abs(extracted - question_data["expected_answer"]) < 0.01

        print(f"  Agent Answer: {result['answer']}")
        print(f"  Tools called: {result.get('tools_called', [])}")
        print(f"  Result: {'CORRECT' if is_correct else 'INCORRECT'}")

        results.append(
            {
                "question_id": question_data["id"],
                "question": question_data["question"],
                "expected": question_data["expected_answer"],
                "extracted_number": extracted,
                "is_correct": is_correct,
                "answer": result["answer"],
                "trace": result.get("trace", []),
                "tools_called": result.get("tools_called", []),
            }
        )

    evaluation = evaluate_results(results)
    print(format_report(results, evaluation))

    output_dir = Path(__file__).parent / "outputs"
    output_dir.mkdir(exist_ok=True)

    output_file = output_dir / "agent_results.json"
    with open(output_file, "w") as f:
        json.dump(
            {
                "metadata": {
                    "course": "BU.330.760.41 - Generative AI in Business",
                    "assignment": "HW3 - Math Agent with Tool Use",
                    "mode": mode,
                    "model_paradigm": "ReAct (Reasoning + Acting) from Yao et al. 2023",
                },
                "results": results,
                "evaluation": evaluation,
            },
            f,
            indent=2,
        )

    print(f"\nResults saved to {output_file}")


if __name__ == "__main__":
    main()
