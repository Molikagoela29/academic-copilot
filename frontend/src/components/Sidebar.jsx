import { useRef, useState } from "react";

const STATUS_LABEL = {
  processing: "Indexing…",
  failed: "Failed",
  ready: null,
};

export default function Sidebar({
  documents,
  readyDocuments,
  selectedDocId,
  onSelectDoc,
  onUpload,
  onDelete,
  health,
}) {
  const fileInputRef = useRef(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const [notice, setNotice] = useState("");

  const handleFileChange = async (event) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;

    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setUploadError("Please select a PDF file.");
      return;
    }

    setIsUploading(true);
    setUploadError("");
    setNotice("");

    try {
      const result = await onUpload(file);
      if (result.duplicate) {
        setNotice(result.message);
        onSelectDoc(result.doc_id);
      } else {
        setNotice("Indexing started — this document will be ready shortly.");
      }
    } catch (error) {
      setUploadError(error.message);
    } finally {
      setIsUploading(false);
    }
  };

  const handleDelete = async (event, doc) => {
    event.stopPropagation();
    if (!window.confirm(`Delete "${doc.filename}" and everything generated from it?`)) {
      return;
    }
    try {
      await onDelete(doc.doc_id);
    } catch (error) {
      setUploadError(error.message);
    }
  };

  const totalChunks = readyDocuments.reduce((sum, doc) => sum + doc.chunks_count, 0);

  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-icon">🎓</div>
        <div>
          <h1>Academic Copilot</h1>
          <p>Study smarter with your notes</p>
        </div>
      </div>

      {health && !health.llm_available && (
        <div className="health-warning" role="alert">
          <strong>Model unavailable</strong>
          <span>{health.detail}</span>
        </div>
      )}

      <div className="upload-card">
        <h3>Upload PDF</h3>
        <p>Add study material to your library.</p>

        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,application/pdf"
          onChange={handleFileChange}
          hidden
        />

        <button
          className="upload-btn"
          onClick={() => fileInputRef.current?.click()}
          disabled={isUploading}
        >
          {isUploading ? "Uploading…" : "+ Add PDF Document"}
        </button>

        {uploadError && <p className="upload-error">{uploadError}</p>}
        {notice && <p className="upload-notice">{notice}</p>}
      </div>

      <div className="document-section">
        <p className="section-title">DOCUMENT LIBRARY ({documents.length})</p>

        <div className="document-list">
          {readyDocuments.length > 1 && (
            <button
              type="button"
              className={`document-card ${selectedDocId === "all" ? "doc-selected" : ""}`}
              onClick={() => onSelectDoc("all")}
            >
              <div className="pdf-icon all-icon">📚</div>
              <div className="document-info">
                <p>All Documents</p>
                <span>{totalChunks} total chunks</span>
              </div>
            </button>
          )}

          {documents.map((doc) => {
            const statusLabel = STATUS_LABEL[doc.status];
            return (
              <div className="document-row" key={doc.doc_id}>
                <button
                  type="button"
                  className={[
                    "document-card",
                    selectedDocId === doc.doc_id ? "doc-selected" : "",
                    doc.status !== "ready" ? `doc-${doc.status}` : "",
                  ]
                    .filter(Boolean)
                    .join(" ")}
                  onClick={() => doc.status === "ready" && onSelectDoc(doc.doc_id)}
                  disabled={doc.status !== "ready"}
                  title={doc.error ?? doc.filename}
                >
                  <div className="pdf-icon">{doc.status === "failed" ? "!" : "PDF"}</div>
                  <div className="document-info">
                    <p>{doc.filename}</p>
                    <span>
                      {statusLabel ?? `${doc.pages} p · ${doc.chunks_count} chunks`}
                    </span>
                  </div>
                </button>
                <button
                  type="button"
                  className="doc-delete-btn"
                  title={`Delete ${doc.filename}`}
                  aria-label={`Delete ${doc.filename}`}
                  onClick={(event) => handleDelete(event, doc)}
                >
                  ✕
                </button>
              </div>
            );
          })}

          {documents.length === 0 && (
            <div className="empty-docs">
              <span>No documents yet. Upload a PDF above to get started.</span>
            </div>
          )}
        </div>
      </div>

      <div className="sidebar-footer">
        <p>Persistent FAISS · Cosine RAG · {health?.llm_model ?? "Llama"}</p>
      </div>
    </aside>
  );
}
