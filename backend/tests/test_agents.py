import json


def test_summary_is_generated_and_saved(client, indexed_doc, fake_llm):
    fake_llm.response = "## Photosynthesis\nLight becomes chemical energy."

    response = client.post("/agents/summarize", json={"doc_id": indexed_doc["doc_id"]})

    assert response.status_code == 200
    body = response.json()
    assert body["summary"].startswith("## Photosynthesis")
    assert body["study_set_id"] is not None

    saved = client.get(f"/study-sets/{body['study_set_id']}").json()
    assert saved["kind"] == "summary"
    assert saved["scope_label"] == "biology.pdf"


def test_summary_can_skip_saving(client, indexed_doc, fake_llm):
    body = client.post("/agents/summarize", json={"save": False}).json()
    assert body["study_set_id"] is None
    assert client.get("/study-sets").json()["study_sets"] == []


def test_quiz_parses_questions_and_saves_the_set(client, indexed_doc, fake_llm):
    fake_llm.response = json.dumps(
        [
            {"question": "Why does photosynthesis matter?", "answer": "It stores energy."},
            {"question": "What do mitochondria do?", "answer": "They respire."},
        ]
    )

    body = client.post(
        "/agents/quiz", json={"num_questions": 2, "doc_id": indexed_doc["doc_id"]}
    ).json()

    assert len(body["questions"]) == 2
    assert body["questions"][0]["question"] == "Why does photosynthesis matter?"
    assert client.get(f"/study-sets/{body['study_set_id']}").json()["kind"] == "quiz"


def test_quiz_tolerates_json_wrapped_in_prose(client, indexed_doc, fake_llm):
    fake_llm.response = (
        'Certainly! Here is your quiz:\n```json\n'
        '[{"question": "What is ATP?", "answer": "An energy carrier."}]\n```\nGood luck!'
    )
    body = client.post("/agents/quiz", json={"num_questions": 1}).json()
    assert body["questions"][0]["question"] == "What is ATP?"


def test_quiz_drops_malformed_entries_but_keeps_valid_ones(client, indexed_doc, fake_llm):
    fake_llm.response = json.dumps(
        [
            {"question": "Valid?", "answer": "Yes."},
            {"question": "", "answer": "Missing question."},
            {"question": "Missing answer."},
            "not an object",
        ]
    )
    body = client.post("/agents/quiz", json={"num_questions": 4}).json()
    assert len(body["questions"]) == 1


def test_unparseable_quiz_output_surfaces_as_502_not_an_empty_list(
    client, indexed_doc, fake_llm
):
    """A silent empty list would look to the user like nothing happened."""
    fake_llm.response = "I'm sorry, I can't do that."

    response = client.post("/agents/quiz", json={"num_questions": 3})

    assert response.status_code == 502
    assert "json" in response.json()["detail"].lower()


def test_quiz_retries_once_before_failing(client, indexed_doc, fake_llm):
    fake_llm.responses = [
        "Sure thing, one moment!",
        json.dumps([{"question": "Recovered?", "answer": "Yes."}]),
    ]
    body = client.post("/agents/quiz", json={"num_questions": 1}).json()
    assert body["questions"][0]["question"] == "Recovered?"
    assert len(fake_llm.prompts) == 2


def test_quiz_size_is_validated(client, indexed_doc, fake_llm):
    assert client.post("/agents/quiz", json={"num_questions": 0}).status_code == 422
    assert client.post("/agents/quiz", json={"num_questions": 500}).status_code == 422


def test_quiz_grading_returns_a_bounded_score(client, indexed_doc, fake_llm):
    fake_llm.response = json.dumps(
        {"score": 75, "verdict": "partially correct", "feedback": "Good start."}
    )

    body = client.post(
        "/agents/quiz/grade",
        json={
            "question": "What is photosynthesis?",
            "expected_answer": "Light to chemical energy.",
            "student_answer": "Plants make food.",
        },
    ).json()

    assert body["score"] == 75
    assert body["verdict"] == "partially correct"
    assert body["feedback"] == "Good start."


def test_grading_clamps_out_of_range_scores_and_derives_a_verdict(
    client, indexed_doc, fake_llm
):
    fake_llm.response = json.dumps(
        {"score": 900, "verdict": "spectacular", "feedback": "Wow."}
    )

    body = client.post(
        "/agents/quiz/grade",
        json={"question": "Q", "expected_answer": "A", "student_answer": "B"},
    ).json()

    assert body["score"] == 100
    assert body["verdict"] == "correct"


def test_flashcards_are_generated_and_deduplicated(client, indexed_doc, fake_llm):
    fake_llm.response = json.dumps(
        [
            {"term": "Photosynthesis", "definition": "Light to chemical energy."},
            {"term": "photosynthesis", "definition": "A duplicate term."},
            {"term": "Mitochondria", "definition": "Site of respiration."},
        ]
    )

    body = client.post("/agents/flashcards", json={"num_cards": 3}).json()

    terms = [card["term"] for card in body["flashcards"]]
    assert terms == ["Photosynthesis", "Mitochondria"]
    assert client.get(f"/study-sets/{body['study_set_id']}").json()["kind"] == "flashcards"


def test_flashcard_count_is_validated(client, indexed_doc, fake_llm):
    assert client.post("/agents/flashcards", json={"num_cards": 0}).status_code == 422
    assert client.post("/agents/flashcards", json={"num_cards": 99}).status_code == 422


def test_agents_require_an_indexed_document(client, fake_llm):
    for path, payload in [
        ("/agents/summarize", {}),
        ("/agents/quiz", {"num_questions": 3}),
        ("/agents/flashcards", {"num_cards": 3}),
    ]:
        assert client.post(path, json=payload).status_code == 409


def test_llm_outage_surfaces_as_503(client, indexed_doc, monkeypatch):
    from app.agents import summary_agent
    from app.core.errors import LLMUnavailable

    def explode(prompt, temperature=None):
        raise LLMUnavailable()

    monkeypatch.setattr(summary_agent.llm_service, "ask_llm", explode)

    response = client.post("/agents/summarize", json={})
    assert response.status_code == 503
    assert "Ollama" in response.json()["detail"]
