from pydantic import BaseModel
from typing import List, Optional


# ─── Documents ────────────────────────────────────────────────────────────────

class DocumentMeta(BaseModel):
    doc_id: str
    filename: str
    pages: int
    chunks_count: int
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
    pages_processed: int
    chunks_created: int
    message: str


# ─── Query / QA ───────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    question: str
    doc_id: Optional[str] = None


class SourceReference(BaseModel):
    filename: str
    page: int
    doc_id: Optional[str] = None


class QueryResponse(BaseModel):
    question: str
    answer: str
    sources: List[SourceReference]


# ─── Summary ──────────────────────────────────────────────────────────────────

class SummaryRequest(BaseModel):
    doc_id: Optional[str] = None


class SummaryResponse(BaseModel):
    summary: str


# ─── Quiz ─────────────────────────────────────────────────────────────────────

class QuizRequest(BaseModel):
    num_questions: int = 5
    doc_id: Optional[str] = None


class QuizQuestion(BaseModel):
    question: str
    answer: str


class QuizResponse(BaseModel):
    questions: List[QuizQuestion]


# ─── Flashcards ───────────────────────────────────────────────────────────────

class FlashcardRequest(BaseModel):
    num_cards: int = 10
    doc_id: Optional[str] = None


class Flashcard(BaseModel):
    term: str
    definition: str


class FlashcardResponse(BaseModel):
    flashcards: List[Flashcard]
