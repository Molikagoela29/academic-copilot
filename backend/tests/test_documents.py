from app.core.config import settings
from app.retrieval import faiss_retriever


def test_listing_documents_reports_status(client, indexed_doc):
    documents = client.get("/documents").json()["documents"]
    assert len(documents) == 1
    assert documents[0]["status"] == "ready"
    assert documents[0]["filename"] == "biology.pdf"


def test_fetching_an_unknown_document_returns_404(client):
    assert client.get("/documents/nope").status_code == 404


def test_original_pdf_is_served_inline_for_page_citations(client, indexed_doc):
    response = client.get(f"/documents/{indexed_doc['doc_id']}/file")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "inline" in response.headers["content-disposition"]
    assert response.content.startswith(b"%PDF-")


def test_deleting_a_document_removes_index_pdf_and_study_sets(
    client, indexed_doc, fake_llm
):
    doc_id = indexed_doc["doc_id"]
    client.post("/agents/summarize", json={"doc_id": doc_id})
    assert client.get("/study-sets").json()["study_sets"]

    assert client.delete(f"/documents/{doc_id}").status_code == 200

    assert client.get("/documents").json()["documents"] == []
    assert not faiss_retriever.is_indexed(doc_id)
    assert list(settings.upload_dir.iterdir()) == []
    assert client.get("/study-sets").json()["study_sets"] == []
    assert not (settings.storage_dir / doc_id).exists()


def test_deleting_an_unknown_document_returns_404(client):
    assert client.delete("/documents/nope").status_code == 404


def test_reconcile_marks_interrupted_ingestion_as_failed(client, indexed_doc):
    from app.db import repository
    from app.services import ingestion_service

    repository.update_document(indexed_doc["doc_id"], status="processing")
    ingestion_service.reconcile()

    document = repository.get_document(indexed_doc["doc_id"])
    assert document["status"] == "failed"
    assert "restart" in document["error"].lower()


def test_reconcile_removes_rows_whose_index_has_vanished(client, indexed_doc):
    from app.db import repository
    from app.services import ingestion_service

    faiss_retriever.drop_document(indexed_doc["doc_id"])
    ingestion_service.reconcile()

    assert repository.get_document(indexed_doc["doc_id"]) == {}
