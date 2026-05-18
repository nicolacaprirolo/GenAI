"""Warm up Ollama model before recording. Run once: python3 warmup.py"""
from openai import OpenAI
c = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
r = c.chat.completions.create(
    model="devstral:latest",
    messages=[{"role": "user", "content": "hi"}],
    max_tokens=5,
)
print("Model warm:", r.choices[0].message.content)
