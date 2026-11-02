from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class Route(StrEnum):
    """Which specialist should handle a question."""

    COST = "cost"
    ANOMALY = "anomaly"
    OPTIMIZATION = "optimization"
    OUT_OF_SCOPE = "out_of_scope"


class Role(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


@dataclass(frozen=True)
class Fact:
    """A number from the analytics engine. The AI refers to it only by its id."""

    id: str
    label: str
    value: str


@dataclass(frozen=True)
class SourceLink:
    title: str
    url: str


@dataclass(frozen=True)
class DocumentPassage:
    title: str
    url: str
    text: str


@dataclass(frozen=True)
class Evidence:
    route: Route
    facts: list[Fact] = field(default_factory=list)
    passages: list[DocumentPassage] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Conversation:
    id: UUID
    title: str
    created_at: datetime


@dataclass(frozen=True)
class Message:
    id: UUID
    role: Role
    content: str
    created_at: datetime
    sources: list[SourceLink] = field(default_factory=list)


@dataclass(frozen=True)
class ChatEvent:
    """One step sent to the browser while an answer is produced."""

    type: str
    text: str = ""
    sources: list[SourceLink] = field(default_factory=list)
