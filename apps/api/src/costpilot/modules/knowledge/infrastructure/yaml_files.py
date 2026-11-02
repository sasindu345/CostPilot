from dataclasses import dataclass
from pathlib import Path

import yaml

from costpilot.modules.knowledge.domain.models import Source


@dataclass(frozen=True)
class SearchQuestion:
    question: str
    provider: str
    expected: tuple[str, ...]


def read_sources(path: str) -> list[Source]:
    return [Source(**item) for item in yaml.safe_load(Path(path).read_text())["sources"]]


def read_questions(path: str) -> list[SearchQuestion]:
    return [
        SearchQuestion(item["question"], item["provider"], tuple(item["expected"]))
        for item in yaml.safe_load(Path(path).read_text())["questions"]
    ]
