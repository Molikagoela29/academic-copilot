import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.agents import router as agents_router
from app.api.conversations import router as conversations_router
from app.api.documents import router as documents_router
from app.api.query import router as query_router
from app.api.study_sets import router as study_sets_router
from app.api.system import router as system_router
from app.api.upload import router as upload_router
from app.core.config import settings
from app.core.errors import CopilotError
from app.core.logging_config import configure_logging
from app.db.database import init_db
from app.retrieval import faiss_retriever
from app.services import ingestion_service

configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.ensure_dirs()
    init_db()
    faiss_retriever.load_all()
    ingestion_service.reconcile()
    logger.info(
        "Academic Copilot ready — model=%s, embeddings=%s",
        settings.ollama_model,
        settings.embedding_model,
    )
    yield
    logger.info("Shutting down")


app = FastAPI(
    title="Academic Copilot API",
    description=(
        "Retrieval-augmented study assistant. Upload PDFs, ask grounded "
        "questions, and generate summaries, quizzes and spaced-repetition "
        "flashcards from your own material."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(CopilotError)
async def handle_copilot_error(request: Request, exc: CopilotError) -> JSONResponse:
    """Application errors carry their own status code and a user-facing message."""
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.exception_handler(RequestValidationError)
async def handle_validation_error(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Flatten pydantic's error list into a single readable sentence."""
    problems = []
    for error in exc.errors():
        location = " → ".join(str(part) for part in error["loc"] if part != "body")
        problems.append(f"{location}: {error['msg']}" if location else error["msg"])
    return JSONResponse(
        status_code=422, content={"detail": "; ".join(problems) or "Invalid request."}
    )


@app.exception_handler(Exception)
async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    """Never leak a stack trace to the client; log it in full instead."""
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected server error occurred. Check the server logs."},
    )


@app.get("/", tags=["system"])
def home() -> dict:
    return {
        "name": "Academic Copilot API",
        "version": app.version,
        "docs": "/docs",
        "health": "/health",
    }


app.include_router(system_router)
app.include_router(upload_router)
app.include_router(query_router)
app.include_router(agents_router)
app.include_router(documents_router)
app.include_router(conversations_router)
app.include_router(study_sets_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
