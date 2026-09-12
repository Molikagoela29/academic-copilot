"""
Shared test fixtures.

Every test runs against a throwaway data directory and a fake embedder, so the
suite needs no model download, no Ollama instance and no network access.
"""

import re
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings  # noqa: E402


@pytest.fixture(autouse=True)
def isolated_environment(tmp_path, monkeypatch):
    """Point all storage at a per-test temporary directory."""
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    # The fake embedder below is lexical, so it cannot reproduce the similarity
    # magnitudes a real sentence-transformer yields for paraphrased text.
    # Ranking is what the tests assert on; test_retrieval covers the threshold.
    monkeypatch.setattr(settings, "min_similarity", 0.0)
    settings.ensure_dirs()

    from app.db import database
    from app.retrieval import faiss_retriever

    database.close_connection()
    database.init_db()
    faiss_retriever.reset()

    yield

    database.close_connection()


@pytest.fixture(autouse=True)
def fake_embedder(monkeypatch):
    """
    Replace the sentence-transformer with a deterministic hashing embedder.

    Word-level hashing into a fixed-width vector keeps the property the tests
    actually depend on: documents sharing vocabulary score higher than those
    that do not.
    """
    dimension = 64

    def fake_encode(texts, normalize=True):
        vectors = np.zeros((len(texts), dimension), dtype="float32")
        for row, text in enumerate(texts):
            for word in text.lower().split():
                vectors[row][hash(word) % dimension] += 1.0
        if normalize:
            norms = np.linalg.norm(vectors, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            vectors = vectors / norms
        return vectors

    from app.embeddings import embedder

    monkeypatch.setattr(embedder, "encode", fake_encode)
    monkeypatch.setattr(embedder, "dimension", lambda: dimension)
    return fake_encode


@pytest.fixture
def fake_llm(monkeypatch):
    """
    Stub the LLM. Tests set `fake_llm.response` (or `.responses` for a queue)
    and read back `fake_llm.prompts` to assert on what was sent.
    """

    class FakeLLM:
        def __init__(self):
            self.response = "A grounded explanation of the topic."
            self.responses = None
            self.prompts = []

        def __call__(self, prompt, temperature=None):
            self.prompts.append(prompt)
            if self.responses:
                return self.responses.pop(0)
            return self.response

        def stream(self, prompt, temperature=None):
            # Real token streams carry their own whitespace; keep it so that
            # joining the tokens reproduces the response exactly.
            return iter(re.findall(r"\S+\s*", self(prompt)))

    fake = FakeLLM()

    from app.agents import quiz_agent, summary_agent, flashcard_agent
    from app.services import llm_service, qa_service

    monkeypatch.setattr(llm_service, "ask_llm", fake)
    monkeypatch.setattr(llm_service, "stream_llm", fake.stream)
    monkeypatch.setattr(qa_service.llm_service, "ask_llm", fake)
    monkeypatch.setattr(qa_service.llm_service, "stream_llm", fake.stream)
    for module in (quiz_agent, summary_agent, flashcard_agent):
        monkeypatch.setattr(module.llm_service, "ask_llm", fake)
        monkeypatch.setattr(module.llm_service, "stream_llm", fake.stream)

    return fake


@pytest.fixture
def client():
    """A TestClient that surfaces unexpected server errors to the test."""
    from fastapi.testclient import TestClient

    import main

    with TestClient(main.app) as test_client:
        yield test_client


@pytest.fixture
def http_client():
    """
    A TestClient that returns 500 responses instead of re-raising.

    TestClient re-raises server exceptions by default, which hides the response
    a real HTTP peer would receive from the global exception handler.
    """
    from fastapi.testclient import TestClient

    import main

    with TestClient(main.app, raise_server_exceptions=False) as test_client:
        yield test_client


@pytest.fixture
def sample_pdf(tmp_path):
    """A small real PDF built with pypdf, so parsing exercises the true path."""
    return _build_pdf(
        tmp_path / "sample.pdf",
        [
            "Photosynthesis converts light energy into chemical energy stored in glucose.",
            "Mitochondria are the organelles responsible for cellular respiration.",
        ],
    )


def _build_pdf(path: Path, page_texts):
    """Write a minimal one-page-per-string PDF by hand (no external tooling)."""
    objects = []
    page_ids = []
    content_ids = []

    for offset, _ in enumerate(page_texts):
        page_ids.append(4 + offset * 2)
        content_ids.append(5 + offset * 2)

    kids = " ".join(f"{pid} 0 R" for pid in page_ids)
    objects.append("1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
    objects.append(
        f"2 0 obj\n<< /Type /Pages /Kids [{kids}] /Count {len(page_texts)} >>\nendobj\n"
    )
    objects.append(
        "3 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
    )

    for text, page_id, content_id in zip(page_texts, page_ids, content_ids):
        objects.append(
            f"{page_id} 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>\nendobj\n"
        )
        escaped = text.replace("(", r"\(").replace(")", r"\)")
        stream = f"BT /F1 12 Tf 72 720 Td ({escaped}) Tj ET"
        objects.append(
            f"{content_id} 0 obj\n<< /Length {len(stream)} >>\nstream\n{stream}\nendstream\nendobj\n"
        )

    pdf = "%PDF-1.4\n"
    offsets = []
    for obj in objects:
        offsets.append(len(pdf))
        pdf += obj

    xref_position = len(pdf)
    pdf += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n"
    for offset in offsets:
        pdf += f"{offset:010d} 00000 n \n"
    pdf += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_position}\n%%EOF\n"
    )

    path.write_bytes(pdf.encode("latin-1"))
    return path


@pytest.fixture
def pdf_factory(tmp_path):
    """Build additional PDFs with custom page text inside a test."""
    counter = {"n": 0}

    def make(page_texts, name=None):
        counter["n"] += 1
        filename = name or f"doc_{counter['n']}.pdf"
        return _build_pdf(tmp_path / filename, page_texts)

    return make


@pytest.fixture
def indexed_doc(client, sample_pdf):
    """Upload and fully index a sample PDF; yields its document metadata."""
    with open(sample_pdf, "rb") as handle:
        response = client.post(
            "/upload", files={"file": ("biology.pdf", handle, "application/pdf")}
        )
    assert response.status_code == 202, response.text
    doc_id = response.json()["doc_id"]

    document = client.get(f"/documents/{doc_id}").json()
    assert document["status"] == "ready", document
    return document
