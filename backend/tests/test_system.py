def test_root_advertises_docs_and_health(client):
    body = client.get("/").json()
    assert body["docs"] == "/docs"
    assert body["health"] == "/health"


def test_health_reports_ok_when_the_model_is_reachable(client, monkeypatch):
    from app.api import system

    monkeypatch.setattr(system.llm_service, "is_available", lambda: True)
    monkeypatch.setattr(system.llm_service, "installed_models", lambda: ["llama3:latest"])

    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["llm_available"] is True
    assert body["detail"] is None


def test_health_reports_degraded_when_ollama_is_unreachable(client, monkeypatch):
    from app.api import system

    monkeypatch.setattr(system.llm_service, "is_available", lambda: False)

    body = client.get("/health").json()
    assert body["status"] == "degraded"
    assert "Cannot reach Ollama" in body["detail"]


def test_health_reports_degraded_when_the_model_is_not_pulled(client, monkeypatch):
    from app.api import system

    monkeypatch.setattr(system.llm_service, "is_available", lambda: True)
    monkeypatch.setattr(system.llm_service, "installed_models", lambda: ["mistral:latest"])

    body = client.get("/health").json()
    assert body["status"] == "degraded"
    assert "ollama pull" in body["detail"]


def test_health_counts_indexed_documents(client, indexed_doc, monkeypatch):
    from app.api import system

    monkeypatch.setattr(system.llm_service, "is_available", lambda: True)
    monkeypatch.setattr(system.llm_service, "installed_models", lambda: ["llama3"])

    assert client.get("/health").json()["documents_indexed"] == 1


def test_unhandled_errors_do_not_leak_internals(
    http_client, client, indexed_doc, monkeypatch
):
    from app.services import qa_service

    def explode(question, doc_id=None):
        raise RuntimeError("secret internal detail")

    monkeypatch.setattr(qa_service, "get_answer", explode)

    response = http_client.post("/query", json={"question": "photosynthesis"})
    assert response.status_code == 500
    assert "secret internal detail" not in response.text


def test_validation_errors_are_flattened_into_one_sentence(client):
    detail = client.post("/query", json={}).json()["detail"]
    assert isinstance(detail, str)
    assert "question" in detail
