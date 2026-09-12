# Academic Copilot — Frontend

React 19 + Vite client for the Academic Copilot API. See the
[project README](../README.md) for the full picture.

## Setup

```bash
npm install
cp .env.example .env   # optional; defaults to http://127.0.0.1:8000
npm run dev
```

| Script | Purpose |
| --- | --- |
| `npm run dev` | Dev server with hot reload |
| `npm run build` | Production build into `dist/` |
| `npm run preview` | Serve the production build locally |
| `npm run lint` | Lint `src/` with oxlint |

## Configuration

`VITE_API_URL` points the client at the backend. It is read at build time, so a
production image must be built with the value it will use (the Dockerfile takes it as a
build arg).

## Structure

```
src/
  api.js                 Single API client — fetch wrapper, error mapping, SSE parsing
  App.jsx                Shell: layout, tabs, document scope
  hooks/useDocuments.js  Document library; polls while ingestion is in progress
  components/
    Sidebar.jsx          Upload, library, indexing status, model health
    ChatPanel.jsx        Streaming chat, history drawer, citation chips
    SummaryPanel.jsx     Streaming summaries + saved summaries
    QuizPanel.jsx        Quiz generation, written answers, AI grading
    FlashcardPanel.jsx   Deck generation and browsing
    ReviewPanel.jsx      SM-2 spaced-repetition session
    PdfViewer.jsx        Modal opening a cited page of the source PDF
    Markdown.jsx         Markdown rendering for all model output
    Spinner.jsx          Loading, empty and error primitives
```

## Notes

Model output is rendered as Markdown (`react-markdown` + `remark-gfm`) — the models emit
headings, lists and tables, which showed as raw syntax when rendered as plain text.

Chat and summary generation stream over server-sent events; every request is cancellable
via `AbortController`, and switching away mid-generation aborts it.
