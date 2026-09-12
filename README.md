# 🎓 Academic Copilot

Academic Copilot is an AI-powered study assistant. Upload your PDF study material, ask
questions grounded in it, and turn it into summaries, quizzes and spaced-repetition
flashcards — all running locally against your own Llama model.

It uses **Retrieval-Augmented Generation (RAG)**: relevant passages are retrieved from
your documents with FAISS and handed to the model, so every answer carries page-level
citations you can click through to the original PDF.

## ✨ Features

**Ask**
- 📄 Upload and index multiple PDFs; indexing runs in the background
- 💬 Streaming answers, rendered as Markdown
- 📚 Page-level citations that open the cited page of the source PDF
- 🎯 Scope questions to one document or search your whole library
- 💾 Chat history persisted across restarts
- 🚫 Says "not found" rather than inventing answers outside your material

**Study**
- 📝 Structured Markdown summaries, streamed as they are written
- 🧠 Open-ended conceptual quizzes, with **AI grading and feedback** on your written answers
- 🃏 Flashcard decks with a **SM-2 spaced-repetition review session**
- 🗂️ Every summary, quiz and deck is saved and can be reopened later

**Operational**
- ♻️ Durable storage: FAISS indices, uploads and SQLite survive restarts
- 🩺 `/health` endpoint reporting whether Ollama and the model are actually available
- 🔒 Upload validation: size limits, PDF signature checks, encrypted-PDF handling, duplicate detection
- 🧪 88 backend tests, Docker Compose, and CI

## 🛠️ Tech Stack

**Backend:** Python 3.9+, FastAPI, pypdf, LangChain text splitters, Sentence Transformers, FAISS, SQLite
**AI/LLM:** Llama via Ollama, Retrieval-Augmented Generation
**Frontend:** React 19, Vite, react-markdown

## ⚙️ How It Works

```text
PDF Upload  ──▶  background ingestion
                      │
                      ├─▶ text extraction (per page)
                      ├─▶ chunking (1000 chars, 150 overlap)
                      ├─▶ SentenceTransformer embeddings (L2 normalised)
                      └─▶ FAISS IndexFlatIP  ──▶  data/storage/<doc_id>/

Question    ──▶  cosine search across the selected scope
                      │
                      ├─▶ top-k chunks + page metadata
                      ├─▶ grounded prompt
                      └─▶ Llama (streamed)  ──▶  Answer + clickable page sources
```

Metadata, chat history, saved study sets and review schedules live in SQLite at
`backend/data/copilot.db`.

## 🚀 Run Locally

### Prerequisites

Three things: **Python 3.11+**, **Node.js 20+**, and **Ollama**. Check what you already
have:

```bash
python3 --version
node --version
ollama --version
```

<details>
<summary>macOS — installing the missing pieces</summary>

macOS ships with Python 3.9, which is **too old** — `numpy`, `faiss-cpu` and the other
pinned dependencies need 3.11 or newer. Install a current Python alongside it.
[Homebrew](https://brew.sh) is the simplest route:

```bash
# Install Homebrew if you don't have it (asks for your admin password)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Apple Silicon only: put brew on your PATH
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"

brew install python@3.12
brew install node
brew install ollama
```

No admin password? [uv](https://docs.astral.sh/uv/) installs a standalone Python into your
home directory instead:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source "$HOME/.local/bin/env"
uv python install 3.12
```

</details>

<details>
<summary>Windows / Linux</summary>

- **Node.js** — [nodejs.org](https://nodejs.org) (LTS installer), or `apt install nodejs npm`
- **Ollama** — [ollama.com/download](https://ollama.com/download)
- **Python 3.11+** — [python.org](https://python.org), or `apt install python3.12 python3.12-venv`

</details>

Then pull a model and start Ollama. Leave it running in its own terminal:

```bash
ollama pull llama3     # ~4.7 GB, one time
ollama serve
```

> Without Ollama the app still starts, and uploading and indexing work — but `/health`
> reports `degraded` and any question returns a 503 explaining that the model is
> unreachable.

### Backend

In a second terminal:

```bash
cd backend
python3.12 -m venv .venv         # any 3.11+ interpreter works
source .venv/bin/activate        # Windows: .venv\Scripts\activate
python -V                        # confirm 3.11 or newer before installing
pip install -r requirements.txt

cp .env.example .env             # optional — defaults work out of the box
uvicorn main:app --reload
```

The API is at `http://127.0.0.1:8000`, interactive docs at `/docs`, and a readiness
check at `/health`.

> The first upload downloads the embedding model (~90 MB). Subsequent runs are instant.

### Frontend

In a third terminal:

```bash
cd frontend
npm install
cp .env.example .env             # optional — defaults to 127.0.0.1:8000
npm run dev
```

Open the URL Vite prints (usually `http://localhost:5173`).

> `npm: command not found` means Node.js is not installed — see Prerequisites above.

### With Docker

Brings up Ollama, pulls the model, and serves the API and UI together:

```bash
docker compose up --build
```

The UI is then on `http://localhost:8080` and the API on `http://localhost:8000`.
The first run downloads the Llama model, so give it a few minutes.

## 🧪 Tests & Checks

**Backend** — 88 tests covering upload validation, retrieval scoping, the SM-2
scheduler, agent JSON parsing, conversations and every error path:

```bash
cd backend
pip install -r requirements-dev.txt
pytest
```

The suite mocks the LLM and the embedding model, so it needs no Ollama instance, no
model download and no network access.

**Frontend** — lint and a production build:

```bash
cd frontend
npm run lint
npm run build
```

Both jobs run on every push via [GitHub Actions](.github/workflows/ci.yml).

## ⚙️ Configuration

Every setting is an environment variable (see `backend/.env.example`):

| Variable | Default | Purpose |
| --- | --- | --- |
| `OLLAMA_URL` | `http://localhost:11434` | Where Ollama is listening |
| `OLLAMA_MODEL` | `llama3` | Model used for all generation |
| `LLM_TIMEOUT` | `180` | Seconds before a generation is abandoned |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence-transformer for retrieval |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | `1000` / `150` | Chunking granularity |
| `RETRIEVAL_K` | `6` | Chunks fed to the model per question |
| `MIN_SIMILARITY` | `0.25` | Cosine floor for a chunk to count as relevant |
| `MAX_UPLOAD_BYTES` | `52428800` | Upload size limit (50 MB) |
| `MAX_PAGES` | `1500` | Page limit per PDF |
| `CORS_ORIGINS` | localhost:5173 | Comma-separated allowed origins |
| `DATA_DIR` | `backend/data` | Uploads, indices and the database |

## 📡 API

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Readiness, including whether the model is installed |
| `POST` | `/upload` | Queue a PDF for background indexing (202) |
| `GET` | `/documents` | List documents and their indexing status |
| `GET` | `/documents/{id}/file` | The original PDF, served inline for citations |
| `DELETE` | `/documents/{id}` | Delete a document, its index, PDF and study sets |
| `POST` | `/query` | Ask a question (complete response) |
| `POST` | `/query/stream` | Ask a question (server-sent events) |
| `GET` | `/conversations` | Chat history |
| `POST` | `/agents/summarize` `/stream` | Generate a summary |
| `POST` | `/agents/quiz` | Generate a conceptual quiz |
| `POST` | `/agents/quiz/grade` | Grade a written answer |
| `POST` | `/agents/flashcards` | Generate a flashcard deck |
| `GET` | `/study-sets` | Saved summaries, quizzes and decks |
| `GET` | `/study-sets/{id}/due` | Cards due for review today |
| `POST` | `/study-sets/{id}/review` | Record a review and reschedule (SM-2) |

Full schemas are at `/docs`.

## 📌 Current Status

The application is feature-complete for **single-user local use**: multiple documents,
persistent storage, streaming answers, clickable citations, chat history, AI-graded
quizzes and spaced-repetition flashcards, all covered by tests and packaged for Docker.

## 🔮 Not Yet Built

These are deliberate boundaries rather than oversights — the app currently assumes one
trusted user on one machine:

- **Authentication and per-user isolation.** The document library is global; anyone who
  can reach the API sees every document. Required before deploying beyond localhost.
- **A scalable vector store.** FAISS indices are held in memory and loaded fully at
  startup, which is fine for dozens of documents but not thousands. Qdrant or pgvector
  would replace `app/retrieval/faiss_retriever.py` behind the same interface.
- **A real task queue.** Ingestion runs in FastAPI background tasks, so it does not
  survive a restart mid-document (such documents are marked failed on the next boot).
- **OCR** for scanned PDFs, which are currently rejected with a clear message.
- **A retrieval evaluation set** to measure whether chunking and `k` changes actually
  improve answer quality.

## 📄 License

MIT — see [LICENSE](LICENSE).
