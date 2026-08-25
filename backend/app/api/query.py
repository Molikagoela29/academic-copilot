from fastapi import APIRouter
from app.models.schemas import QueryRequest, QueryResponse
from app.services import qa_service

router = APIRouter()


@router.post("/query", response_model=QueryResponse)
def query_ai(request: QueryRequest):
    result = qa_service.get_answer(request.question, doc_id=request.doc_id)

    return QueryResponse(
        question=request.question,
        answer=result["answer"],
        sources=result["sources"],
    )