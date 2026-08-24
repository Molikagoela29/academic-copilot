from pydantic import BaseModel
from typing import List


# ─── Upload ───────────────────────────────────────────────────────────────────

class UploadResponse(BaseModel):
    filename: str
    pages_processed: int
    chunks_created: int
    message: str


# ─── Query / QA ───────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    question: str


class SourceReference(BaseModel):
    filename: str
    page: int


class QueryResponse(BaseModel):
    question: str
    answer: str
    sources: List[SourceReference]


# ─── Summary ──────────────────────────────────────────────────────────────────

class SummaryResponse(BaseModel):
    summary: str


# ─── Quiz ─────────────────────────────────────────────────────────────────────

class QuizRequest(BaseModel):
    num_questions: int = 5


class QuizQuestion(BaseModel):
    question: str
    answer: str


class QuizResponse(BaseModel):
    questions: List[QuizQuestion]


# ─── Flashcards ───────────────────────────────────────────────────────────────

class FlashcardRequest(BaseModel):
    num_cards: int = 10


class Flashcard(BaseModel):
    term: str
    definition: str


class FlashcardResponse(BaseModel):
    flashcards: List[Flashcard]
