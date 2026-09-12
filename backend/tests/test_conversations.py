def test_a_query_starts_a_conversation_titled_from_the_question(
    client, indexed_doc, fake_llm
):
    fake_llm.response = "Light energy becomes glucose."
    conversation_id = client.post(
        "/query", json={"question": "What is photosynthesis?"}
    ).json()["conversation_id"]

    conversation = client.get(f"/conversations/{conversation_id}").json()
    assert conversation["title"] == "What is photosynthesis?"
    assert [message["role"] for message in conversation["messages"]] == [
        "user",
        "assistant",
    ]
    assert conversation["messages"][1]["content"] == "Light energy becomes glucose."


def test_history_persists_sources_alongside_the_answer(client, indexed_doc, fake_llm):
    conversation_id = client.post(
        "/query", json={"question": "photosynthesis light glucose"}
    ).json()["conversation_id"]

    messages = client.get(f"/conversations/{conversation_id}").json()["messages"]
    assert messages[1]["sources"]
    assert messages[1]["sources"][0]["filename"] == "biology.pdf"


def test_follow_up_questions_append_to_the_same_conversation(
    client, indexed_doc, fake_llm
):
    first = client.post("/query", json={"question": "photosynthesis"}).json()
    conversation_id = first["conversation_id"]

    client.post(
        "/query",
        json={"question": "mitochondria respiration", "conversation_id": conversation_id},
    )

    conversation = client.get(f"/conversations/{conversation_id}").json()
    assert len(conversation["messages"]) == 4
    assert len(client.get("/conversations").json()["conversations"]) == 1


def test_a_long_question_is_truncated_for_the_title(client, indexed_doc, fake_llm):
    question = "photosynthesis " * 30
    conversation_id = client.post("/query", json={"question": question}).json()[
        "conversation_id"
    ]
    title = client.get(f"/conversations/{conversation_id}").json()["title"]
    assert len(title) <= 61
    assert title.endswith("…")


def test_conversations_can_be_created_renamed_and_deleted(client):
    conversation = client.post("/conversations", json={"title": "Exam prep"}).json()
    assert conversation["title"] == "Exam prep"

    renamed = client.patch(
        f"/conversations/{conversation['id']}", json={"title": "Finals"}
    ).json()
    assert renamed["title"] == "Finals"

    assert client.delete(f"/conversations/{conversation['id']}").status_code == 204
    assert client.get(f"/conversations/{conversation['id']}").status_code == 404


def test_deleting_a_conversation_removes_its_messages(client, indexed_doc, fake_llm):
    from app.db import repository

    conversation_id = client.post("/query", json={"question": "photosynthesis"}).json()[
        "conversation_id"
    ]
    client.delete(f"/conversations/{conversation_id}")

    assert repository.list_messages(conversation_id) == []


def test_unknown_conversation_returns_404(client):
    assert client.get("/conversations/999").status_code == 404
    assert client.delete("/conversations/999").status_code == 404
