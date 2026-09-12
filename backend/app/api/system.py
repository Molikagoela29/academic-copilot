from fastapi import APIRouter

from app.core.config import settings
from app.models.schemas import HealthResponse
from app.retrieval import faiss_retriever
from app.services import llm_service

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """
    Readiness probe. Reports degraded (still HTTP 200) when Ollama is
    unreachable or the configured model is not installed, so the client can warn
    the user before they wait on a request that cannot succeed.
    """
    llm_available = llm_service.is_available()
    detail = None

    if not llm_available:
        detail = f"Cannot reach Ollama at {settings.ollama_url}."
    else:
        installed = llm_service.installed_models()
        # Ollama reports tags as `name:tag`; a bare model name matches any tag.
        if installed and not any(
            model == settings.ollama_model or model.split(":")[0] == settings.ollama_model
            for model in installed
        ):
            llm_available = False
            detail = (
                f"Model '{settings.ollama_model}' is not installed. "
                f"Run: ollama pull {settings.ollama_model}"
            )

    return HealthResponse(
        status="ok" if llm_available else "degraded",
        llm_available=llm_available,
        llm_model=settings.ollama_model,
        embedding_model=settings.embedding_model,
        documents_indexed=len(faiss_retriever.indexed_ids()),
        detail=detail,
    )
