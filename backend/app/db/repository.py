"""Thin data-access helpers over the SQLite schema."""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.db.database import get_connection, transaction


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_to_dict(row) -> Dict[str, Any]:
    return dict(row) if row is not None else {}


# ─── Documents ────────────────────────────────────────────────────────────────

def create_document(
    doc_id: str,
    filename: str,
    stored_filename: str,
    file_hash: Optional[str],
    status: str = "processing",
) -> Dict[str, Any]:
    with transaction() as conn:
        conn.execute(
            """
            INSERT INTO documents
                (doc_id, filename, stored_filename, file_hash, status, upload_time)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (doc_id, filename, stored_filename, file_hash, status, _now()),
        )
    return get_document(doc_id)


def update_document(doc_id: str, **fields) -> None:
    if not fields:
        return
    allowed = {"pages", "chunks_count", "status", "error", "file_hash"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return

    assignments = ", ".join(f"{key} = ?" for key in updates)
    with transaction() as conn:
        conn.execute(
            f"UPDATE documents SET {assignments} WHERE doc_id = ?",
            (*updates.values(), doc_id),
        )


def get_document(doc_id: str) -> Dict[str, Any]:
    row = get_connection().execute(
        "SELECT * FROM documents WHERE doc_id = ?", (doc_id,)
    ).fetchone()
    return _row_to_dict(row)


def get_document_by_hash(file_hash: str) -> Dict[str, Any]:
    row = get_connection().execute(
        "SELECT * FROM documents WHERE file_hash = ?", (file_hash,)
    ).fetchone()
    return _row_to_dict(row)


def list_documents() -> List[Dict[str, Any]]:
    rows = get_connection().execute(
        "SELECT * FROM documents ORDER BY upload_time DESC"
    ).fetchall()
    return [dict(row) for row in rows]


def delete_document(doc_id: str) -> bool:
    with transaction() as conn:
        cursor = conn.execute("DELETE FROM documents WHERE doc_id = ?", (doc_id,))
    return cursor.rowcount > 0


# ─── Conversations & messages ─────────────────────────────────────────────────

def create_conversation(title: str, doc_id: Optional[str] = None) -> Dict[str, Any]:
    now = _now()
    with transaction() as conn:
        cursor = conn.execute(
            "INSERT INTO conversations (title, doc_id, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (title, doc_id, now, now),
        )
    return get_conversation(cursor.lastrowid)


def get_conversation(conversation_id: int) -> Dict[str, Any]:
    row = get_connection().execute(
        "SELECT * FROM conversations WHERE id = ?", (conversation_id,)
    ).fetchone()
    return _row_to_dict(row)


def list_conversations() -> List[Dict[str, Any]]:
    rows = get_connection().execute(
        """
        SELECT c.*, COUNT(m.id) AS message_count
        FROM conversations c
        LEFT JOIN messages m ON m.conversation_id = c.id
        GROUP BY c.id
        ORDER BY c.updated_at DESC
        """
    ).fetchall()
    return [dict(row) for row in rows]


def rename_conversation(conversation_id: int, title: str) -> bool:
    with transaction() as conn:
        cursor = conn.execute(
            "UPDATE conversations SET title = ?, updated_at = ? WHERE id = ?",
            (title, _now(), conversation_id),
        )
    return cursor.rowcount > 0


def delete_conversation(conversation_id: int) -> bool:
    with transaction() as conn:
        cursor = conn.execute(
            "DELETE FROM conversations WHERE id = ?", (conversation_id,)
        )
    return cursor.rowcount > 0


def add_message(
    conversation_id: int,
    role: str,
    content: str,
    sources: Optional[List[dict]] = None,
) -> Dict[str, Any]:
    now = _now()
    with transaction() as conn:
        cursor = conn.execute(
            """
            INSERT INTO messages (conversation_id, role, content, sources, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (conversation_id, role, content, json.dumps(sources or []), now),
        )
        conn.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (now, conversation_id),
        )
    row = conn.execute(
        "SELECT * FROM messages WHERE id = ?", (cursor.lastrowid,)
    ).fetchone()
    return _decode_message(row)


def list_messages(conversation_id: int) -> List[Dict[str, Any]]:
    rows = get_connection().execute(
        "SELECT * FROM messages WHERE conversation_id = ? ORDER BY id ASC",
        (conversation_id,),
    ).fetchall()
    return [_decode_message(row) for row in rows]


def _decode_message(row) -> Dict[str, Any]:
    if row is None:
        return {}
    message = dict(row)
    try:
        message["sources"] = json.loads(message.get("sources") or "[]")
    except json.JSONDecodeError:
        message["sources"] = []
    return message


# ─── Study sets (summaries, quizzes, flashcard decks) ─────────────────────────

def create_study_set(
    kind: str,
    doc_id: Optional[str],
    scope_label: str,
    payload: Any,
) -> Dict[str, Any]:
    with transaction() as conn:
        cursor = conn.execute(
            """
            INSERT INTO study_sets (kind, doc_id, scope_label, payload, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (kind, doc_id, scope_label, json.dumps(payload), _now()),
        )
    return get_study_set(cursor.lastrowid)


def get_study_set(study_set_id: int) -> Dict[str, Any]:
    row = get_connection().execute(
        "SELECT * FROM study_sets WHERE id = ?", (study_set_id,)
    ).fetchone()
    return _decode_study_set(row)


def list_study_sets(
    kind: Optional[str] = None, doc_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    query = "SELECT * FROM study_sets WHERE 1 = 1"
    params: List[Any] = []
    if kind:
        query += " AND kind = ?"
        params.append(kind)
    if doc_id:
        query += " AND doc_id = ?"
        params.append(doc_id)
    query += " ORDER BY created_at DESC"

    rows = get_connection().execute(query, params).fetchall()
    return [_decode_study_set(row) for row in rows]


def delete_study_set(study_set_id: int) -> bool:
    with transaction() as conn:
        cursor = conn.execute("DELETE FROM study_sets WHERE id = ?", (study_set_id,))
    return cursor.rowcount > 0


def delete_study_sets_for_document(doc_id: str) -> int:
    with transaction() as conn:
        cursor = conn.execute("DELETE FROM study_sets WHERE doc_id = ?", (doc_id,))
    return cursor.rowcount


def _decode_study_set(row) -> Dict[str, Any]:
    if row is None:
        return {}
    study_set = dict(row)
    try:
        study_set["payload"] = json.loads(study_set.get("payload") or "null")
    except json.JSONDecodeError:
        study_set["payload"] = None
    return study_set


# ─── Spaced repetition state ──────────────────────────────────────────────────

def get_card_review(study_set_id: int, card_index: int) -> Dict[str, Any]:
    row = get_connection().execute(
        "SELECT * FROM card_reviews WHERE study_set_id = ? AND card_index = ?",
        (study_set_id, card_index),
    ).fetchone()
    return _row_to_dict(row)


def list_card_reviews(study_set_id: int) -> List[Dict[str, Any]]:
    rows = get_connection().execute(
        "SELECT * FROM card_reviews WHERE study_set_id = ? ORDER BY card_index",
        (study_set_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def upsert_card_review(
    study_set_id: int,
    card_index: int,
    repetitions: int,
    interval_days: int,
    ease: float,
    due_date: str,
) -> Dict[str, Any]:
    with transaction() as conn:
        conn.execute(
            """
            INSERT INTO card_reviews
                (study_set_id, card_index, repetitions, interval_days, ease, due_date, last_reviewed)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(study_set_id, card_index) DO UPDATE SET
                repetitions   = excluded.repetitions,
                interval_days = excluded.interval_days,
                ease          = excluded.ease,
                due_date      = excluded.due_date,
                last_reviewed = excluded.last_reviewed
            """,
            (
                study_set_id,
                card_index,
                repetitions,
                interval_days,
                ease,
                due_date,
                _now(),
            ),
        )
    return get_card_review(study_set_id, card_index)
