from fastapi import APIRouter

from app.core.errors import CopilotError
from app.db import repository
from app.models.schemas import (
    ConversationCreateRequest,
    ConversationDetail,
    ConversationListResponse,
    ConversationMeta,
    ConversationRenameRequest,
    MessageOut,
)

router = APIRouter(prefix="/conversations", tags=["conversations"])


class ConversationNotFound(CopilotError):
    status_code = 404
    default_message = "Conversation not found."


@router.get("", response_model=ConversationListResponse)
def list_conversations() -> ConversationListResponse:
    """Chat history, most recently active first."""
    return ConversationListResponse(
        conversations=[
            ConversationMeta(**conversation)
            for conversation in repository.list_conversations()
        ]
    )


@router.post("", response_model=ConversationDetail, status_code=201)
def create_conversation(request: ConversationCreateRequest) -> ConversationDetail:
    conversation = repository.create_conversation(
        title=request.title, doc_id=request.doc_id
    )
    return ConversationDetail(**conversation, messages=[])


@router.get("/{conversation_id}", response_model=ConversationDetail)
def get_conversation(conversation_id: int) -> ConversationDetail:
    """A single conversation with its full message history."""
    conversation = repository.get_conversation(conversation_id)
    if not conversation:
        raise ConversationNotFound()

    messages = [
        MessageOut(
            id=message["id"],
            role=message["role"],
            content=message["content"],
            sources=message["sources"],
            created_at=message["created_at"],
        )
        for message in repository.list_messages(conversation_id)
    ]
    return ConversationDetail(**conversation, messages=messages)


@router.patch("/{conversation_id}", response_model=ConversationMeta)
def rename_conversation(
    conversation_id: int, request: ConversationRenameRequest
) -> ConversationMeta:
    if not repository.rename_conversation(conversation_id, request.title):
        raise ConversationNotFound()
    return ConversationMeta(**repository.get_conversation(conversation_id))


@router.delete("/{conversation_id}", status_code=204)
def delete_conversation(conversation_id: int) -> None:
    if not repository.delete_conversation(conversation_id):
        raise ConversationNotFound()
