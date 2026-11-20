"""Model access: a thin Anthropic client wrapper plus a deterministic mock for offline tests."""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from dataclasses import dataclass, field

STRONG_MODEL = os.environ.get("PILOT_STRONG_MODEL", "claude-sonnet-5-5")
WEAK_MODEL = os.environ.get("PILOT_WEAK_MODEL", "claude-haiku-5-5")
# Grader defaults to a different model than the debaters to reduce self-agreement bias.
GRADER_MODEL = os.environ.get("PILOT_GRADER_MODEL", "claude-opus-5-5")
MAX_TOKENS = int(os.environ.get("PILOT_MAX_TOKENS", "1200"))


@dataclass
class Usage:
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    by_model: dict = field(default_factory=dict)

    def add(self, model: str, inp: int, out: int) -> None:
        self.calls += 1
        self.input_tokens += inp
        self.output_tokens += out
        m = self.by_model.setdefault(model, {"calls": 0, "input_tokens": 0, "output_tokens": 0})
        m["calls"] += 1
        m["input_tokens"] += inp
        m["output_tokens"] += out


class Client:
    """Calls the Claude API. Requires ANTHROPIC_API_KEY in the environment."""

    def __init__(self) -> None:
        import anthropic  # imported lazily so mock mode needs no SDK

        self._client = anthropic.Anthropic()
        self.usage = Usage()

    def complete(self, model: str, system: str, messages: list[dict], role: str = "") -> str:
        delay = 2.0
        for attempt in range(5):
            try:
                resp = self._client.messages.create(
                    model=model, max_tokens=MAX_TOKENS, system=system, messages=messages
                )
                self.usage.add(model, resp.usage.input_tokens, resp.usage.output_tokens)
                return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
            except Exception as exc:
                status = getattr(exc, "status_code", None)
                transient = status is None or status in (408, 409, 429) or status >= 500
                if attempt == 4 or not transient:  # do not retry bad requests or auth errors
                    raise
                print(f"  API error ({type(exc).__name__}); retrying in {delay:.0f}s")
                time.sleep(delay)
                delay *= 2
        raise RuntimeError("unreachable")


def preflight(client, models) -> None:
    """Fail fast on a missing key or an unavailable model before spending on a full run."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY is not set. Export it and rerun.")
    for m in sorted(set(models)):
        try:
            client._client.messages.create(
                model=m, max_tokens=5, messages=[{"role": "user", "content": "Reply OK."}]
            )
        except Exception as exc:
            raise SystemExit(f"Preflight failed for model {m}: {exc}. Set PILOT_*_MODEL to a model you can access.")
        print(f"  preflight ok: {m}")


class MockClient:
    """Deterministic stand-in used by tests and --mock runs. Produces no real findings."""

    def __init__(self) -> None:
        self.usage = Usage()

    def complete(self, model: str, system: str, messages: list[dict], role: str = "") -> str:
        text = messages[-1]["content"]
        self.usage.add(model, len(text) // 4, 50)
        h = int(hashlib.sha256((role + text).encode()).hexdigest(), 16)
        if role == "grader":
            return json.dumps({"correct": h % 2 == 0, "reason": "mock grade"})
        if role == "honesty_probe":
            return json.dumps({"memo_has_error": h % 2 == 0, "description": "mock"})
        if role.startswith("judge_verdict") or role == "judge_pushback":
            verdict = "error" if h % 3 else "no_error"
            return json.dumps(
                {"verdict": verdict, "confidence": 0.6, "error_description": "mock", "quote": ""}
            )
        if role == "judge_question":
            return "What is the basis for the key number in your conclusion?"
        return f"[mock {role} turn]"


def parse_json(text: str) -> dict | None:
    """Extract the first JSON object from a model reply. Returns None if none parses."""
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    candidates = [fenced.group(1)] if fenced else []
    start = text.find("{")
    while start != -1:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    candidates.append(text[start : i + 1])
                    break
        start = text.find("{", start + 1)
    for c in candidates:
        try:
            obj = json.loads(c)
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            continue
    return None
