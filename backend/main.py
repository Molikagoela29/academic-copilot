from fastapi import FastAPI

app = FastAPI(
    title="Academic Copilot API",
    description="AI-powered Academic Assistant",
    version="1.0.0"
)


@app.get("/")
def home():
    return {
        "message": "Academic Copilot API is running!",
        "status": "success"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }