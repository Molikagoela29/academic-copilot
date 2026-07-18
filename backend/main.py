from fastapi import FastAPI
from app.api.upload import router as upload_router
from app.api.query import router as query_router

app = FastAPI()

@app.get("/")
def home():
    return {"message": "AI PDF Backend Running 🚀 (Ollama Mode)"}

app.include_router(upload_router)
app.include_router(query_router)