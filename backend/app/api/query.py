from fastapi import APIRouter
from pydantic import BaseModel
import requests
import numpy as np
from sentence_transformers import SentenceTransformer

router = APIRouter()


class QueryRequest(BaseModel):
    question: str


# Stores current PDF chunks and FAISS index
stored_chunks = []
stored_index = []


# Load embedding model once
model = SentenceTransformer("all-MiniLM-L6-v2")


# ---------------------------------
# Ollama / Llama
# ---------------------------------
def ask_llm(prompt: str) -> str:

    url = "http://localhost:11434/api/generate"

    payload = {
        "model": "llama3",
        "prompt": prompt,
        "stream": False
    }

    response = requests.post(
        url,
        json=payload
    )

    response.raise_for_status()

    return response.json()["response"]


# ---------------------------------
# Retrieve relevant chunks
# ---------------------------------
def retrieve_relevant_chunks(question: str, k=3, distance_threshold=1.2):

    if not stored_index:
        return []

    index = stored_index[0]

    query_embedding = model.encode(
        [question]
    )

    query_embedding = np.array(
        query_embedding
    ).astype("float32")

    distances, indices = index.search(
        query_embedding,
        k
    )

    results = []

    for distance, idx in zip(distances[0], indices[0]):

        if (
            0 <= idx < len(stored_chunks)
            and distance <= distance_threshold
        ):
            results.append(
                stored_chunks[idx]
            )

    return results


# ---------------------------------
# Generate answer
# ---------------------------------
def get_answer(question: str):

    if not stored_index:
        return {
            "answer": "No document uploaded.",
            "sources": []
        }

    retrieved_chunks = retrieve_relevant_chunks(
        question
    )

    if not retrieved_chunks:
        return {
            "answer": "Not found.",
            "sources": []
        }

    # Join only the text portion for Llama
    context = "\n\n".join(
        chunk["text"]
        for chunk in retrieved_chunks
    )

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

    # ---------------------------------
    # No sources for unsupported query
    # ---------------------------------
    if answer.lower().startswith("not found"):
        return {
            "answer": "Not found.",
            "sources": []
        }

    # ---------------------------------
    # Create source list
    # ---------------------------------
    sources = []

    for chunk in retrieved_chunks:

        source = {
            "filename": chunk["filename"],
            "page": chunk["page"]
        }

        # Avoid duplicate page citations
        if source not in sources:
            sources.append(source)

    return {
        "answer": answer,
        "sources": sources
    }


# ---------------------------------
# API endpoint
# ---------------------------------
@router.post("/query")
def query_ai(request: QueryRequest):

    result = get_answer(
        request.question
    )

    return {
        "question": request.question,
        "answer": result["answer"],
        "sources": result["sources"]
    }