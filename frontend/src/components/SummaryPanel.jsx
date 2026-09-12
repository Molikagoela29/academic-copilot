import { useEffect, useRef, useState } from "react";

import { api } from "../api";
import Markdown from "./Markdown";
import { EmptyState, ErrorBanner, Thinking } from "./Spinner";

export default function SummaryPanel({ scopeLabel, docId, hasDocuments }) {
  const [summary, setSummary] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState([]);
  const abortRef = useRef(null);

  const refreshSaved = async () => {
    try {
      const data = await api.listStudySets("summary");
      setSaved(data.study_sets ?? []);
    } catch {
      // Saved summaries are a convenience; failing to list them is not fatal.
    }
  };

  useEffect(() => {
    refreshSaved();
    return () => abortRef.current?.abort();
  }, []);

  const generate = async () => {
    const controller = new AbortController();
    abortRef.current = controller;

    setIsGenerating(true);
    setError("");
    setSummary("");

    let accumulated = "";

    try {
      await api.summarizeStream(
        { doc_id: docId, save: true },
        {
          token: (data) => {
            accumulated += data.text;
            setSummary(accumulated);
          },
        },
        controller.signal,
      );
      refreshSaved();
    } catch (err) {
      if (err.name !== "AbortError") setError(err.message);
    } finally {
      setIsGenerating(false);
      abortRef.current = null;
    }
  };

  const openSaved = async (id) => {
    try {
      const studySet = await api.getStudySet(id);
      setSummary(studySet.payload?.summary ?? "");
      setError("");
    } catch (err) {
      setError(err.message);
    }
  };

  const removeSaved = async (event, id) => {
    event.stopPropagation();
    try {
      await api.deleteStudySet(id);
      refreshSaved();
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="tool-panel">
      <div className="tool-header">
        <div>
          <h2>📄 Document Summary</h2>
          <p>
            Summarising: <strong>{scopeLabel}</strong>
          </p>
        </div>
        <div className="tool-controls">
          {isGenerating && (
            <button className="ghost-btn" onClick={() => abortRef.current?.abort()}>
              Stop
            </button>
          )}
          <button
            className="tool-action-btn"
            onClick={generate}
            disabled={isGenerating || !hasDocuments}
          >
            {isGenerating ? "Summarising…" : summary ? "Regenerate" : "Generate Summary"}
          </button>
        </div>
      </div>

      <SavedStrip items={saved} onOpen={openSaved} onRemove={removeSaved} />

      <ErrorBanner message={error} onDismiss={() => setError("")} />

      {summary ? (
        <div className="summary-content">
          <Markdown>{summary}</Markdown>
          {isGenerating && <Thinking />}
        </div>
      ) : isGenerating ? (
        <div className="tool-loading">
          <Thinking />
          <p>Reading through {scopeLabel}…</p>
        </div>
      ) : (
        <EmptyState icon="📄">
          Click <strong>Generate Summary</strong> for an AI-written overview of{" "}
          {scopeLabel}.
        </EmptyState>
      )}
    </div>
  );
}

export function SavedStrip({ items, onOpen, onRemove, label = "Saved" }) {
  if (!items?.length) return null;
  return (
    <div className="saved-strip">
      <span className="saved-label">{label}</span>
      {items.map((item) => (
        <span className="saved-chip" key={item.id}>
          <button
            type="button"
            className="saved-open"
            onClick={() => onOpen(item.id)}
            title={`${item.scope_label} · ${new Date(item.created_at).toLocaleString()}`}
          >
            {item.scope_label}
            {item.item_count > 1 ? ` (${item.item_count})` : ""}
          </button>
          <button
            type="button"
            className="saved-remove"
            aria-label={`Delete saved set: ${item.scope_label}`}
            onClick={(event) => onRemove(event, item.id)}
          >
            ✕
          </button>
        </span>
      ))}
    </div>
  );
}
