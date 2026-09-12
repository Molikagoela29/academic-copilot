from typing import Any, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

DocStatus = Literal["processing", "ready", "failed"]


# ─── Documents ────────────────────────────────────────────────────────────────

class DocumentMeta(BaseModel):
    doc_id: str
    filename: str
    pages: int
    chunks_count: int
    status: DocStatus
    error: Optional[str] = None
    upload_time: str


class DocumentListResponse(BaseModel):
    documents: List[DocumentMeta]


class DocumentDeleteResponse(BaseModel):
    success: bool
    message: str


# ─── Upload ───────────────────────────────────────────────────────────────────

class UploadResponse(BaseModel):
    doc_id: str
    filename: str
    status: DocStatus
    duplicate: bool = False
    message: str


# ─── Query / QA ───────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    doc_id: Optional[str] = None
    conversation_id: Optional[int] = None

    @field_validator("question")
    @classmethod
    def _strip_question(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Question cannot be empty.")
        return stripped


class SourceReference(BaseModel):
    filename: str
    page: int
    doc_id: Optional[str] = None


class QueryResponse(BaseModel):
    question: str
    answer: str
    sources: List[SourceReference]
    conversation_id: Optional[int] = None


# ─── Conversations ────────────────────────────────────────────────────────────

class MessageOut(BaseModel):
    id: int
    role: Literal["user", "assistant"]
    content: str
    sources: List[SourceReference] = []
    created_at: str


class ConversationMeta(BaseModel):
    id: int
    title: str
    doc_id: Optional[str] = None
    message_count: int = 0
    created_at: str
    updated_at: str


class ConversationListResponse(BaseModel):
    conversations: List[ConversationMeta]


class ConversationDetail(BaseModel):
    id: int
    title: str
    doc_id: Optional[str] = None
    created_at: str
    updated_at: str
    messages: List[MessageOut]


class ConversationCreateRequest(BaseModel):
    title: str = Field(default="New chat", min_length=1, max_length=200)
    doc_id: Optional[str] = None


class ConversationRenameRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)


# ─── Summary ──────────────────────────────────────────────────────────────────

class SummaryRequest(BaseModel):
    doc_id: Optional[str] = None
    save: bool = True


class SummaryResponse(BaseModel):
    summary: str
    study_set_id: Optional[int] = None


# ─── Quiz ─────────────────────────────────────────────────────────────────────

class QuizRequest(BaseModel):
    num_questions: int = Field(default=5, ge=1, le=15)
    doc_id: Optional[str] = None
    save: bool = True


class QuizQuestion(BaseModel):
    question: str
    answer: str


class QuizResponse(BaseModel):
    questions: List[QuizQuestion]
    study_set_id: Optional[int] = None


class QuizGradeRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    expected_answer: str = Field(min_length=1, max_length=8000)
    student_answer: str = Field(min_length=1, max_length=8000)


class QuizGradeResponse(BaseModel):
    score: int = Field(ge=0, le=100)
    verdict: str
    feedback: str


# ─── Flashcards ───────────────────────────────────────────────────────────────

class FlashcardRequest(BaseModel):
    num_cards: int = Field(default=10, ge=1, le=30)
    doc_id: Optional[str] = None
    save: bool = True


class Flashcard(BaseModel):
    term: str
    definition: str


class FlashcardResponse(BaseModel):
    flashcards: List[Flashcard]
    study_set_id: Optional[int] = None


# ─── Study sets & spaced repetition ───────────────────────────────────────────

class StudySetMeta(BaseModel):
    id: int
    kind: Literal["summary", "quiz", "flashcards"]
    doc_id: Optional[str] = None
    scope_label: str
    item_count: int
    created_at: str


class StudySetListResponse(BaseModel):
    study_sets: List[StudySetMeta]


class StudySetDetail(BaseModel):
    id: int
    kind: Literal["summary", "quiz", "flashcards"]
    doc_id: Optional[str] = None
    scope_label: str
    payload: Any
    created_at: str


class CardState(BaseModel):
    card_index: int
    repetitions: int
    interval_days: int
    ease: float
    due_date: str
    last_reviewed: Optional[str] = None
    due_now: bool


class DueCard(BaseModel):
    card_index: int
    term: str
    definition: str
    state: CardState


class DueCardsResponse(BaseModel):
    study_set_id: int
    scope_label: str
    total_cards: int
    due_cards: List[DueCard]


class ReviewRequest(BaseModel):
    card_index: int = Field(ge=0)
    quality: Literal["again", "hard", "good", "easy"]


class ReviewResponse(BaseModel):
    state: CardState
    next_review_in_days: int


# ─── System ───────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    llm_available: bool
    llm_model: str
    embedding_model: str
    documents_indexed: int
    detail: Optional[str] = None


class ErrorResponse(BaseModel):
    detail: str
