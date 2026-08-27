from typing import Optional
import requests
from app.retrieval import faiss_retriever

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3"


def ask_llm(prompt: str) -> str:
    """Send a prompt to the local Ollama/Llama instance and return the response."""
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
    }
    response = requests.post(OLLAMA_URL, json=payload)
    response.raise_for_status()
    return response.json()["response"]


def get_answer(question: str, doc_id: Optional[str] = None) -> dict:
    """
    Full RAG pipeline:
      1. Retrieve relevant chunks via FAISS (filtered by doc_id if provided)
      2. Build a study-assistant prompt
      3. Call Llama
      4. Return answer + source references
    """
    if not faiss_retriever.has_documents():
        return {"answer": "No document uploaded.", "sources": []}

    retrieved_chunks = faiss_retriever.retrieve(question, doc_id=doc_id)

    if not retrieved_chunks:
        return {"answer": "Not found.", "sources": []}

    context = "\n\n".join(chunk["text"] for chunk in retrieved_chunks)

    prompt = f"""
You are an Academic Copilot helping a student understand their study material.

Use the provided study material as your primary source.

You may:
- explain concepts in simpler language
- provide helpful examples
- compare related concepts
- explain step-by-step
- summarize the material
- rephrase difficult concepts for a beginner

Do not answer unrelated questions using outside knowledge.

If the answer cannot reasonably be found or explained from the provided
study material, respond exactly with:

Not found.

Study Material:
{context}

Student Question:
{question}

Answer:
"""

    answer = ask_llm(prompt).strip()

    if answer.lower().startswith("not found"):
        return {"answer": "Not found.", "sources": []}

    # Deduplicate citations
    sources = []
    for chunk in retrieved_chunks:
        source = {
            "filename": chunk["filename"],
            "page": chunk["page"],
            "doc_id": chunk.get("doc_id"),
        }
        if source not in sources:
            sources.append(source)

    return {"answer": answer, "sources": sources}
