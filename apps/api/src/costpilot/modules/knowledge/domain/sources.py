"""Rules for what may enter the knowledge base."""

import hashlib
from urllib.parse import urlsplit

from costpilot.modules.knowledge.domain.errors import SourceRejectedError
from costpilot.modules.knowledge.domain.models import Source


def check_trusted_url(url: str, allowed_hosts: tuple[str, ...]) -> None:
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.hostname not in allowed_hosts:
        raise SourceRejectedError(f"Not a trusted address: {url}")


def check_sources(sources: list[Source], allowed_hosts: tuple[str, ...]) -> None:
    identifiers = [source.id for source in sources]
    if len(identifiers) != len(set(identifiers)):
        raise SourceRejectedError("Two sources share the same id.")
    for source in sources:
        check_trusted_url(source.url, allowed_hosts)


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()
