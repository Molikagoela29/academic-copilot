# 🎓 Academic Copilot

Academic Copilot is an AI-powered study assistant that allows students to upload PDF study material and ask questions directly from their documents.

It uses **Retrieval-Augmented Generation (RAG)** to retrieve relevant content from uploaded PDFs and generates context-aware explanations using **Llama**. Answers also include page-level source references for verification.

## ✨ Features

- 📄 Upload and process PDF study material
- 💬 Ask questions directly from uploaded documents
- 🧠 Simplify and explain difficult concepts
- 🔍 Semantic search using FAISS
- 📚 Page-level source references
- 🚫 Handles questions not covered by the uploaded material
- 💻 Interactive React-based chat interface
- 🔄 Auto-scroll and clear-chat functionality

## 🛠️ Tech Stack

**Backend:** Python, FastAPI, PyPDF, LangChain, Sentence Transformers, FAISS, NumPy  
**AI/LLM:** Llama via Ollama, Retrieval-Augmented Generation (RAG)  
**Frontend:** React, JavaScript, Vite, CSS

## ⚙️ How It Works

```text
PDF Upload
    ↓
Text Extraction & Chunking
    ↓
SentenceTransformer Embeddings
    ↓
FAISS Vector Search
    ↓
Relevant Context Retrieval
    ↓
Llama
    ↓
Answer + Source Pages
```

## 🚀 Run Locally

### Backend

```bash
python -m venv venv
venv\Scripts\activate
pip install -r backend/requirements.txt

cd backend
uvicorn main:app --reload
```

Make sure **Ollama** is running with the required Llama model.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Then open the local URL provided by Vite.

## 🔮 Planned Improvements

- Persistent document and FAISS index storage
- Multiple PDF support
- Study material summarization
- Quiz and flashcard generation
- Improved document management

## 📌 Current Status

The core RAG pipeline and frontend are functional. The application currently supports one active PDF at a time, with document persistence and additional study tools planned for future versions.