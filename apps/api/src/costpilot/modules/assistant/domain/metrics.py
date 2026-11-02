"""Measures one answer: AI calls, tokens and how long each step took."""

import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field

MILLISECONDS = 1000


@dataclass
class AnswerMeter:
    ai_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    step_ms: dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self._started = time.perf_counter()

    def add_ai_call(self, input_tokens: int = 0, output_tokens: int = 0) -> None:
        self.ai_calls += 1
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens

    @contextmanager
    def step(self, name: str) -> Iterator[None]:
        started = time.perf_counter()
        try:
            yield
        finally:
            spent = round((time.perf_counter() - started) * MILLISECONDS)
            self.step_ms[name] = self.step_ms.get(name, 0) + spent

    def summary(self) -> dict[str, object]:
        return {
            "ai_calls": self.ai_calls,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_ms": round((time.perf_counter() - self._started) * MILLISECONDS),
            "step_ms": self.step_ms,
        }
