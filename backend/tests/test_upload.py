from app.core.config import settings


def test_upload_indexes_a_pdf_and_reports_ready(client, sample_pdf):
    with open(sample_pdf, "rb") as handle:
        response = client.post(
            "/upload", files={"file": ("biology.pdf", handle, "application/pdf")}
        )

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "processing"
    assert body["duplicate"] is False

    document = client.get(f"/documents/{body['doc_id']}").json()
    assert document["status"] == "ready"
    assert document["pages"] == 2
    assert document["chunks_count"] > 0


def test_non_pdf_extension_is_rejected_with_400(client):
    response = client.post(
        "/upload", files={"file": ("notes.txt", b"plain text", "text/plain")}
    )
    assert response.status_code == 400
    assert "Only PDF files" in response.json()["detail"]


def test_file_with_pdf_extension_but_wrong_signature_is_rejected(client):
    response = client.post(
        "/upload", files={"file": ("fake.pdf", b"not really a pdf", "application/pdf")}
    )
    assert response.status_code == 400
    assert "signature" in response.json()["detail"].lower()


def test_empty_file_is_rejected(client):
    response = client.post(
        "/upload", files={"file": ("empty.pdf", b"", "application/pdf")}
    )
    assert response.status_code == 400


def test_oversized_file_is_rejected(client, monkeypatch):
    monkeypatch.setattr(settings, "max_upload_bytes", 100)
    payload = b"%PDF-1.4\n" + b"x" * 500

    response = client.post(
        "/upload", files={"file": ("big.pdf", payload, "application/pdf")}
    )
    assert response.status_code == 400
    assert "too large" in response.json()["detail"].lower()


def test_pdf_with_no_extractable_text_is_marked_failed(client, pdf_factory):
    blank = pdf_factory(["   "], name="blank.pdf")
    with open(blank, "rb") as handle:
        response = client.post(
            "/upload", files={"file": ("blank.pdf", handle, "application/pdf")}
        )

    document = client.get(f"/documents/{response.json()['doc_id']}").json()
    assert document["status"] == "failed"
    assert "no readable text" in document["error"].lower()


def test_reuploading_the_same_file_is_detected_as_a_duplicate(client, sample_pdf):
    for _ in range(2):
        with open(sample_pdf, "rb") as handle:
            response = client.post(
                "/upload", files={"file": ("biology.pdf", handle, "application/pdf")}
            )

    assert response.json()["duplicate"] is True
    assert len(client.get("/documents").json()["documents"]) == 1


def test_filename_cannot_escape_the_upload_directory(client, sample_pdf):
    with open(sample_pdf, "rb") as handle:
        response = client.post(
            "/upload",
            files={"file": ("../../../evil.pdf", handle, "application/pdf")},
        )

    assert response.status_code == 202
    stored = list(settings.upload_dir.iterdir())
    assert len(stored) == 1
    assert stored[0].parent == settings.upload_dir
    assert ".." not in stored[0].name
