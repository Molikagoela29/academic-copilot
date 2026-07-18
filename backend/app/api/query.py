from fastapi import APIRouter
from pydantic import BaseModel
import requests
import numpy as np
from sentence_transformers import SentenceTransformer

router = APIRouter()

class QueryRequest(BaseModel):
    question: str


stored_chunks = []
stored_index = []

model = SentenceTransformer('all-MiniLM-L6-v2')


def ask_llm(prompt: str) -> str:
    url = "http://localhost:11434/api/generate"

    payload = {
        "model": "llama3",
        "prompt": prompt,
        "stream": False
    }

    response = requests.post(url, json=payload)
    return response.json()["response"]


def retrieve_relevant_chunks(question, k=3):
    if not stored_index:
        return "No document uploaded."

    index = stored_index[0]
    query_embedding = model.encode([question])

    distances, indices = index.search(
        np.array(query_embedding).astype("float32"), k
    )

    results = []
    for idx in indices[0]:
        if idx < len(stored_chunks):
            results.append(stored_chunks[idx])

    return "\n\n".join(results)


def get_answer(question: str):
    context = retrieve_relevant_chunks(question)

    prompt = f"""
    Answer ONLY using the context below.
    If not found, say "Not found".

    Context:
    {context}

    Question:
    {question}
    """

    return ask_llm(prompt)


# 🔥 THIS WAS MISSING
@router.post("/query")
def query_ai(request: QueryRequest):
    return {
        "question": request.question,
        "answer": get_answer(request.question)
    }