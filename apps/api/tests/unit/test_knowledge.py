"""Uses a real in-memory Qdrant, and a fake embedder that needs no API key."""

import hashlib
import math
import re
from collections.abc import Sequence
from pathlib import Path

import httpx2
import pytest
from qdrant_client import AsyncQdrantClient

from costpilot.modules.knowledge.application.indexer import KnowledgeIndexer
from costpilot.modules.knowledge.application.search_service import KnowledgeSearchService
from costpilot.modules.knowledge.domain.errors import (
    KnowledgeUnavailableError,
    SourceRejectedError,
)
from costpilot.modules.knowledge.domain.models import Source
from costpilot.modules.knowledge.domain.sources import check_sources
from costpilot.modules.knowledge.infrastructure.html_page_loader import (
    HtmlPageLoader,
    readable_text,
)
from costpilot.modules.knowledge.infrastructure.langchain_splitter import LangChainTextSplitter
from costpilot.modules.knowledge.infrastructure.qdrant_index import QdrantVectorIndex
from costpilot.modules.knowledge.infrastructure.yaml_files import read_questions, read_sources

HOSTS = ("docs.example.test",)
DIMENSIONS = 64
KNOWLEDGE_FOLDER = Path(__file__).parents[4] / "knowledge"
S3_TEXT = "s3 lifecycle rules move rarely read objects to cheaper storage classes"
EBS_TEXT = "ebs gp3 volumes cost less than gp2 volumes for the same size"


def source(identifier, provider="aws"):
    return Source(identifier, provider, "storage", identifier, f"https://{HOSTS[0]}/{identifier}")


class WordEmbedder:
    """Similar words give similar vectors, which is enough to test the whole flow."""

    def __init__(self):
        self.documents_embedded = 0

    def _vector(self, text: str) -> list[float]:
        vector = [0.0] * DIMENSIONS
        for word in re.findall(r"\w+", text.lower()):
            vector[int(hashlib.sha256(word.encode()).hexdigest(), 16) % DIMENSIONS] += 1.0
        size = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / size for value in vector]

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        self.documents_embedded += len(texts)
        return [self._vector(text) for text in texts]

    async def embed_query(self, text: str) -> list[float]:
        return self._vector(text)


class FakeLoader:
    def __init__(self, pages):
        self.pages = pages

    async def load(self, item):
        page = self.pages[item.id]
        if isinstance(page, Exception):
            raise page
        return page


class PlainSplitter:
    def split(self, text):
        return [text]


@pytest.fixture
def index():
    return QdrantVectorIndex(AsyncQdrantClient(location=":memory:"), "docs", DIMENSIONS)


@pytest.fixture
def embedder():
    return WordEmbedder()


def indexer(pages, embedder, index):
    return KnowledgeIndexer(FakeLoader(pages), PlainSplitter(), embedder, index, HOSTS)


def searcher(embedder, index, min_score=0.2):
    return KnowledgeSearchService(embedder, index, limit=3, min_score=min_score)


async def test_search_finds_the_right_document(embedder, index):
    pages = {"s3": S3_TEXT, "ebs": EBS_TEXT}
    await indexer(pages, embedder, index).run([source("s3"), source("ebs")])

    result = await searcher(embedder, index).search(
        "cheaper storage for rarely read objects", "aws"
    )

    assert result.is_available
    assert result.passages[0].source_id == "s3"
    assert result.passages[0].url.endswith("/s3")


async def test_running_again_costs_nothing_and_changes_nothing(embedder, index):
    pages = {"s3": S3_TEXT}
    await indexer(pages, embedder, index).run([source("s3")])
    embedded = embedder.documents_embedded

    report = await indexer(pages, embedder, index).run([source("s3")])

    assert report.unchanged == ["s3"]
    assert report.indexed == []
    assert embedder.documents_embedded == embedded


async def test_a_changed_page_replaces_its_old_text(embedder, index):
    await indexer({"s3": S3_TEXT}, embedder, index).run([source("s3")])

    report = await indexer({"s3": EBS_TEXT}, embedder, index).run([source("s3")])

    result = await searcher(embedder, index).search("gp3 volumes", "aws")
    assert report.indexed == ["s3"]
    assert len(result.passages) == 1
    assert "gp3" in result.passages[0].text


async def test_a_source_taken_off_the_list_is_removed(embedder, index):
    await indexer({"s3": S3_TEXT, "ebs": EBS_TEXT}, embedder, index).run(
        [source("s3"), source("ebs")]
    )

    report = await indexer({"s3": S3_TEXT}, embedder, index).run([source("s3")])

    assert report.removed == ["ebs"]
    assert (await searcher(embedder, index).search("gp3 volumes", "aws")).passages == []


async def test_one_bad_page_does_not_stop_the_others(embedder, index):
    pages = {"bad": KnowledgeUnavailableError("down"), "s3": S3_TEXT}

    report = await indexer(pages, embedder, index).run([source("bad"), source("s3")])

    assert report.failed == ["bad"]
    assert report.indexed == ["s3"]


async def test_advice_for_one_cloud_is_never_given_for_another(embedder, index):
    await indexer({"s3": S3_TEXT}, embedder, index).run([source("s3", provider="aws")])

    result = await searcher(embedder, index).search("cheaper storage classes", "azure")

    assert result.is_available
    assert result.passages == []


async def test_weak_matches_are_dropped(embedder, index):
    await indexer({"s3": S3_TEXT}, embedder, index).run([source("s3")])

    result = await searcher(embedder, index, min_score=0.9).search("cheaper storage", "aws")

    assert result.passages == []


async def test_search_being_down_is_reported_not_raised(embedder):
    class BrokenIndex:
        async def search(self, vector, provider, limit, min_score):
            raise KnowledgeUnavailableError("down")

    result = await searcher(embedder, BrokenIndex()).search("anything", "aws")

    assert result.is_available is False
    assert result.passages == []


async def test_a_missing_collection_is_reported_as_unavailable(embedder, index):
    result = await searcher(embedder, index).search("anything", "aws")

    assert result.is_available is False


def test_only_trusted_sites_are_accepted():
    bad = Source("x", "aws", "t", "t", "https://evil.test/page")

    with pytest.raises(SourceRejectedError):
        check_sources([bad], HOSTS)


def test_plain_http_is_refused():
    bad = Source("x", "aws", "t", "t", f"http://{HOSTS[0]}/page")

    with pytest.raises(SourceRejectedError):
        check_sources([bad], HOSTS)


def test_duplicate_ids_are_refused():
    with pytest.raises(SourceRejectedError):
        check_sources([source("a"), source("a")], HOSTS)


def test_readable_text_keeps_the_article_and_drops_the_rest():
    html = """<html><body><nav>Menu</nav>
    <div id="main-content"><h1>Lifecycle</h1><script>steal()</script><p>Move objects.</p></div>
    <footer>Footer</footer></body></html>"""

    assert readable_text(html) == "Lifecycle\nMove objects."


def loader(handler):
    return HtmlPageLoader(
        HOSTS, max_bytes=10_000, timeout_seconds=1, transport=httpx2.MockTransport(handler)
    )


async def test_loader_reads_a_page():
    page = f"<main>{'useful text ' * 30}</main>"

    text = await loader(lambda _: httpx2.Response(200, text=page)).load(source("page"))

    assert text.startswith("useful text")


async def test_loader_refuses_a_redirect_to_an_untrusted_site():
    def handler(request):
        if request.url.host == HOSTS[0]:
            return httpx2.Response(302, headers={"location": "https://evil.test/page"})
        return httpx2.Response(200, text="<main>evil</main>")

    with pytest.raises(SourceRejectedError):
        await loader(handler).load(source("page"))


async def test_loader_refuses_an_oversized_page():
    big = "x" * 20_000

    with pytest.raises(SourceRejectedError):
        await loader(lambda _: httpx2.Response(200, text=big)).load(source("page"))


async def test_loader_reports_a_missing_page():
    with pytest.raises(KnowledgeUnavailableError):
        await loader(lambda _: httpx2.Response(404)).load(source("page"))


def test_splitter_keeps_chunks_within_size():
    chunks = LangChainTextSplitter(100, 10).split("word " * 200)

    assert len(chunks) > 1
    assert all(len(chunk) <= 100 for chunk in chunks)


def test_the_real_source_list_is_valid():
    sources = read_sources(str(KNOWLEDGE_FOLDER / "sources.yaml"))

    check_sources(sources, ("docs.aws.amazon.com",))
    assert len(sources) >= 15


def test_every_test_question_points_at_a_real_source():
    sources = {item.id for item in read_sources(str(KNOWLEDGE_FOLDER / "sources.yaml"))}
    questions = read_questions(str(KNOWLEDGE_FOLDER / "search-questions.yaml"))

    assert all(set(item.expected) <= sources for item in questions)
