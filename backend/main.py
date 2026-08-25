from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.upload import router as upload_router
from app.api.query import router as query_router
from app.api.agents import router as agents_router
from app.api.documents import router as documents_router
from app.retrieval import faiss_retriever


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load all persisted document indices on startup
    faiss_retriever.load_all()
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {"message": "AI PDF Backend Running 🚀 (Ollama Mode)"}


app.include_router(upload_router)
app.include_router(query_router)
app.include_router(agents_router)
app.include_router(documents_router)