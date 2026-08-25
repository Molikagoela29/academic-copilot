from fastapi import APIRouter, HTTPException
from app.models.schemas import DocumentListResponse, DocumentMeta, DocumentDeleteResponse
from app.retrieval import faiss_retriever

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("", response_model=DocumentListResponse)
def get_documents():
    """List all indexed documents and their metadata."""
    docs = faiss_retriever.list_documents()
    return DocumentListResponse(
        documents=[DocumentMeta(**doc) for doc in docs]
    )


@router.delete("/{doc_id}", response_model=DocumentDeleteResponse)
def delete_document(doc_id: str):
    """Delete an indexed document from memory and disk."""
    success = faiss_retriever.delete_document(doc_id)
    if not success:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return DocumentDeleteResponse(
        success=True,
        message=f"Document {doc_id} deleted successfully."
    )
