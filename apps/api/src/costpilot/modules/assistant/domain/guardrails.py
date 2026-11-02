"""Coded safety checks. These rules work the same way every time, and need no AI."""

import re
from collections.abc import Iterable
from dataclasses import dataclass

from costpilot.modules.assistant.domain.models import Fact
from costpilot.modules.assistant.domain.placeholders import PLACEHOLDER

INJECTION = re.compile(
    r"(ignore|disregard|forget|override|bypass)\b.{0,40}\b(instruction|instructions|rules?|prompt)"
    r"|(reveal|show|print|repeat)\b.{0,40}\b(system prompt|your (instructions|rules|prompt))"
    r"|\b(system prompt|developer mode|jailbreak)\b"
    r"|\byou are now\b"
    r"|\bpretend (to be|you are)\b"
    r"|<\s*/?\s*(system|facts|documents|limitations)\s*>",
    re.IGNORECASE | re.DOTALL,
)
SENTENCE_END = re.compile(r"(?<=[.!?])\s+|\n+")
TYPED_NUMBERS = (
    re.compile(r"[$€£¥]\s*\d"),
    re.compile(
        r"\d[\d,]*(?:\.\d+)?\s*(?:USD|EUR|GBP|JPY|dollars?|euros?|pounds?)\b", re.IGNORECASE
    ),
    re.compile(r"\d[\d,.]*\s*(?:%|percent\b)", re.IGNORECASE),
    re.compile(r"(?<![\w.])\d[\d,]*\.\d+(?![\w.])"),
    re.compile(r"(?<![\w.,])\d{1,3}(?:,\d{3})+(?![\w,])"),
)


def looks_like_injection(text: str) -> bool:
    return INJECTION.search(text) is not None


def typed_numbers(text: str) -> list[str]:
    """Find money or percentages written directly. Years, gp3 and 6 months are fine."""
    without_placeholders = PLACEHOLDER.sub("", text)
    return [m[0] for pattern in TYPED_NUMBERS for m in pattern.finditer(without_placeholders)]


def _subject_word(subject: str) -> str:
    """ "EC2-Instances" is matched as "ec2", so "your EC2 cost" counts as naming it."""
    return re.split(r"[-\s]", subject.strip().lower(), maxsplit=1)[0]


def misplaced_facts(answer: str, facts: Iterable[Fact]) -> list[str]:
    """Find a number used in a sentence that does not name what the number is about."""
    subjects = {fact.id: _subject_word(fact.subject) for fact in facts if fact.subject}
    misplaced = []
    for sentence in SENTENCE_END.split(answer):
        for fact_id in PLACEHOLDER.findall(sentence):
            word = subjects.get(fact_id)
            if word and word not in sentence.lower():
                misplaced.append(fact_id)
    return misplaced


@dataclass(frozen=True)
class AnswerCheck:
    typed: list[str]
    unknown_ids: list[str]
    misplaced: list[str]

    @property
    def passed(self) -> bool:
        return not self.typed and not self.unknown_ids and not self.misplaced


def check_answer(answer: str, facts: Iterable[Fact]) -> AnswerCheck:
    """Runs on the AI's raw text, so a number copied from chat history is caught too."""
    fact_list = list(facts)
    known = {fact.id for fact in fact_list}
    used = PLACEHOLDER.findall(answer)
    return AnswerCheck(
        typed_numbers(answer),
        [fact_id for fact_id in used if fact_id not in known],
        misplaced_facts(answer, fact_list),
    )
