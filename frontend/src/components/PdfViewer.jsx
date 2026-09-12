import { useEffect } from "react";

import { api } from "../api";

/**
 * Modal showing a cited page of the original PDF.
 *
 * Uses the browser's built-in PDF viewer via `#page=N` rather than pulling in a
 * rendering library — the backend already serves the file inline.
 */
export default function PdfViewer({ source, onClose }) {
  useEffect(() => {
    const onKeyDown = (event) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  if (!source) return null;

  const url = api.documentFileUrl(source.doc_id, source.page);

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div
        className="pdf-modal"
        role="dialog"
        aria-label={`${source.filename}, page ${source.page}`}
        onClick={(event) => event.stopPropagation()}
      >
        <header className="pdf-modal-header">
          <div>
            <h3>{source.filename}</h3>
            <p>Page {source.page}</p>
          </div>
          <div className="pdf-modal-actions">
            <a href={url} target="_blank" rel="noopener noreferrer">
              Open in new tab
            </a>
            <button onClick={onClose} aria-label="Close">
              ✕
            </button>
          </div>
        </header>
        <iframe src={url} title={`${source.filename} page ${source.page}`} />
      </div>
    </div>
  );
}
