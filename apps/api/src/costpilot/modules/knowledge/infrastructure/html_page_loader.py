import httpx2
from bs4 import BeautifulSoup

from costpilot.modules.knowledge.domain.errors import (
    KnowledgeUnavailableError,
    SourceRejectedError,
)
from costpilot.modules.knowledge.domain.models import Source
from costpilot.modules.knowledge.domain.sources import check_trusted_url

MAIN_CONTENT = ("#main-content", "main", "article")
NOISE = ("script", "style", "nav", "header", "footer", "aside", "noscript")
MIN_TEXT_LENGTH = 200


def readable_text(html: str) -> str:
    """Keep the page's main text, and drop menus and page furniture."""
    soup = BeautifulSoup(html, "html.parser")
    root = next(filter(None, map(soup.select_one, MAIN_CONTENT)), soup.body or soup)
    for element in root.find_all(NOISE):
        element.decompose()
    lines = (line.strip() for line in root.get_text("\n").splitlines())
    return "\n".join(line for line in lines if line)


class HtmlPageLoader:
    def __init__(
        self,
        allowed_hosts: tuple[str, ...],
        max_bytes: int,
        timeout_seconds: float,
        transport: httpx2.AsyncBaseTransport | None = None,
    ) -> None:
        self._allowed_hosts = allowed_hosts
        self._max_bytes = max_bytes
        self._timeout_seconds = timeout_seconds
        self._transport = transport

    async def load(self, source: Source) -> str:
        check_trusted_url(source.url, self._allowed_hosts)
        async with httpx2.AsyncClient(
            transport=self._transport, timeout=self._timeout_seconds
        ) as client:
            try:
                response = await client.get(source.url, follow_redirects=True)
            except httpx2.HTTPError as error:
                raise KnowledgeUnavailableError(str(error)) from error
        check_trusted_url(str(response.url), self._allowed_hosts)
        if response.status_code != httpx2.codes.OK:
            raise KnowledgeUnavailableError(f"Status {response.status_code}: {source.url}")
        if len(response.content) > self._max_bytes:
            raise SourceRejectedError(f"Page too large: {source.url}")
        text = readable_text(response.text)
        if len(text) < MIN_TEXT_LENGTH:
            raise SourceRejectedError(f"Page has too little text: {source.url}")
        return text
