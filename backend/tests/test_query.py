import json


def test_query_returns_answer_with_page_sources(client, indexed_doc, fake_llm):
    fake_llm.response = "Photosynthesis stores light energy as glucose."

    response = client.post(
        "/query", json={"question": "What is photosynthesis?", "doc_id": indexed_doc["doc_id"]}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "Photosynthesis stores light energy as glucose."
    assert body["sources"]
    assert body["sources"][0]["filename"] == "biology.pdf"
    assert body["sources"][0]["page"] >= 1
    assert body["conversation_id"] is not None


def test_retrieved_context_is_passed_to_the_model(client, indexed_doc, fake_llm):
    client.post("/query", json={"question": "photosynthesis light energy glucose"})
    assert "Photosynthesis" in fake_llm.prompts[0]


def test_not_found_answer_drops_its_sources(client, indexed_doc, fake_llm):
    fake_llm.response = "Not found."
    body = client.post("/query", json={"question": "photosynthesis energy"}).json()
    assert body["answer"] == "Not found."
    assert body["sources"] == []


def test_query_without_any_documents_returns_409(client, fake_llm):
    response = client.post("/query", json={"question": "Anything?"})
    assert response.status_code == 409
    assert "upload" in response.json()["detail"].lower()


def test_query_scoped_to_an_unknown_document_returns_404(client, indexed_doc, fake_llm):
    response = client.post(
        "/query", json={"question": "photosynthesis", "doc_id": "does-not-exist"}
    )
    assert response.status_code == 404


def test_scoping_restricts_retrieval_to_the_selected_document(
    client, indexed_doc, pdf_factory, fake_llm
):
    other = pdf_factory(["Roman aqueducts carried water into imperial cities."])
    with open(other, "rb") as handle:
        second = client.post(
            "/upload", files={"file": ("history.pdf", handle, "application/pdf")}
        ).json()

    body = client.post(
        "/query",
        json={"question": "Roman aqueducts water cities", "doc_id": indexed_doc["doc_id"]},
    ).json()

    assert all(source["doc_id"] == indexed_doc["doc_id"] for source in body["sources"])

    body = client.post(
        "/query", json={"question": "Roman aqueducts water cities", "doc_id": second["doc_id"]}
    ).json()
    assert all(source["filename"] == "history.pdf" for source in body["sources"])


def test_empty_question_is_rejected_with_422(client, indexed_doc):
    assert client.post("/query", json={"question": "   "}).status_code == 422


def test_streaming_query_emits_meta_tokens_and_done(client, indexed_doc, fake_llm):
    fake_llm.response = "Light energy becomes chemical energy"

    with client.stream(
        "POST", "/query/stream", json={"question": "photosynthesis light energy"}
    ) as response:
        assert response.status_code == 200
        raw = "".join(response.iter_text())

    events = _parse_sse(raw)
    assert [event for event, _ in events if event == "meta"]
    assert [event for event, _ in events if event == "token"]

    done = [data for event, data in events if event == "done"][0]
    assert done["answer"] == "Light energy becomes chemical energy"
    assert done["sources"]


def test_streaming_reports_llm_failure_as_an_error_event(client, indexed_doc, monkeypatch):
    from app.core.errors import LLMUnavailable
    from app.services import qa_service

    def explode(prompt, temperature=None):
        raise LLMUnavailable()

    monkeypatch.setattr(qa_service.llm_service, "stream_llm", explode)

    with client.stream(
        "POST", "/query/stream", json={"question": "photosynthesis"}
    ) as response:
        raw = "".join(response.iter_text())

    errors = [data for event, data in _parse_sse(raw) if event == "error"]
    assert errors and "Ollama" in errors[0]["detail"]


def _parse_sse(raw):
    events = []
    for block in raw.strip().split("\n\n"):
        if not block.strip():
            continue
        name, payload = None, None
        for line in block.splitlines():
            if line.startswith("event: "):
                name = line[len("event: "):]
            elif line.startswith("data: "):
                payload = json.loads(line[len("data: "):])
        if name:
            events.append((name, payload))
    return events
