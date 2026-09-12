import pytest

from app.core.errors import DocumentNotFound
from app.retrieval import faiss_retriever


@pytest.fixture
def two_documents():
    faiss_retriever.build_and_register_index(
        doc_id="bio",
        filename="biology.pdf",
        chunks=[
            {"text": "photosynthesis converts light into glucose", "page": 1},
            {"text": "mitochondria drive cellular respiration", "page": 2},
        ],
    )
    faiss_retriever.build_and_register_index(
        doc_id="hist",
        filename="history.pdf",
        chunks=[{"text": "roman aqueducts carried water into cities", "page": 1}],
    )


def test_retrieval_ranks_the_most_similar_chunk_first(two_documents):
    results = faiss_retriever.retrieve("photosynthesis light glucose")
    assert results[0]["text"].startswith("photosynthesis")
    assert results[0]["score"] > 0


def test_retrieval_searches_every_document_when_unscoped(two_documents):
    results = faiss_retriever.retrieve("roman aqueducts water cities", k=5)
    assert any(chunk["filename"] == "history.pdf" for chunk in results)


def test_scoping_excludes_other_documents(two_documents):
    results = faiss_retriever.retrieve("roman aqueducts water", doc_id="bio", k=5)
    assert all(chunk["doc_id"] == "bio" for chunk in results)


def test_unknown_doc_id_raises_rather_than_widening_scope(two_documents):
    """A stale selection must not silently search every document instead."""
    with pytest.raises(DocumentNotFound):
        faiss_retriever.retrieve("photosynthesis", doc_id="deleted-doc")

    with pytest.raises(DocumentNotFound):
        faiss_retriever.get_chunks(doc_id="deleted-doc")


def test_similarity_threshold_filters_weak_matches(two_documents):
    assert faiss_retriever.retrieve("photosynthesis", min_similarity=0.0)
    assert faiss_retriever.retrieve("photosynthesis", min_similarity=1.01) == []


def test_k_limits_the_number_of_results(two_documents):
    assert len(faiss_retriever.retrieve("photosynthesis light", k=1)) == 1


def test_chunks_are_tagged_with_their_document(two_documents):
    for chunk in faiss_retriever.get_chunks(doc_id="bio"):
        assert chunk["doc_id"] == "bio"
        assert chunk["filename"] == "biology.pdf"


def test_indices_survive_a_reload_from_disk(two_documents):
    faiss_retriever.reset()
    assert not faiss_retriever.has_documents()

    assert faiss_retriever.load_all() == 2
    results = faiss_retriever.retrieve("photosynthesis light glucose")
    assert results[0]["text"].startswith("photosynthesis")


def test_dropping_a_document_removes_it_from_disk_and_memory(two_documents):
    assert faiss_retriever.drop_document("bio") is True
    assert faiss_retriever.indexed_ids() == ["hist"]

    faiss_retriever.reset()
    assert faiss_retriever.load_all() == 1


def test_dropping_an_unknown_document_reports_false():
    assert faiss_retriever.drop_document("never-existed") is False
