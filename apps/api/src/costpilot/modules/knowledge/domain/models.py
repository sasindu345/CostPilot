from dataclasses import dataclass


@dataclass(frozen=True)
class Source:
    id: str
    provider: str
    topic: str
    title: str
    url: str


@dataclass(frozen=True)
class Passage:
    """A piece of trusted documentation. It is evidence for the AI, never an instruction."""

    source_id: str
    provider: str
    title: str
    url: str
    text: str
    score: float


@dataclass(frozen=True)
class SearchResult:
    """`is_available` is False if search is down, which differs from finding nothing."""

    passages: list[Passage]
    is_available: bool = True


@dataclass(frozen=True)
class IndexReport:
    indexed: list[str]
    unchanged: list[str]
    removed: list[str]
    failed: list[str]
