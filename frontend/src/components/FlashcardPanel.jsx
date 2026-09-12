import { useEffect, useRef, useState } from "react";

import { api } from "../api";
import ReviewPanel from "./ReviewPanel";
import { EmptyState, ErrorBanner, ToolLoading } from "./Spinner";
import { SavedStrip } from "./SummaryPanel";

export default function FlashcardPanel({ scopeLabel, docId, hasDocuments }) {
  const [flashcards, setFlashcards] = useState([]);
  const [studySetId, setStudySetId] = useState(null);
  const [numCards, setNumCards] = useState(10);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState("");
  const [flipped, setFlipped] = useState({});
  const [saved, setSaved] = useState([]);
  const [mode, setMode] = useState("browse");
  const abortRef = useRef(null);

  const refreshSaved = async () => {
    try {
      const data = await api.listStudySets("flashcards");
      setSaved(data.study_sets ?? []);
    } catch {
      // Non-fatal.
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
    setFlashcards([]);
    setFlipped({});
    setMode("browse");

    try {
      const data = await api.generateFlashcards(
        { num_cards: numCards, doc_id: docId, save: true },
        controller.signal,
      );
      setFlashcards(data.flashcards ?? []);
      setStudySetId(data.study_set_id);
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
      setFlashcards(studySet.payload ?? []);
      setStudySetId(id);
      setFlipped({});
      setMode("browse");
      setError("");
    } catch (err) {
      setError(err.message);
    }
  };

  const removeSaved = async (event, id) => {
    event.stopPropagation();
    try {
      await api.deleteStudySet(id);
      if (id === studySetId) {
        setFlashcards([]);
        setStudySetId(null);
      }
      refreshSaved();
    } catch (err) {
      setError(err.message);
    }
  };

  if (mode === "review" && studySetId) {
    return (
      <ReviewPanel
        studySetId={studySetId}
        onExit={() => setMode("browse")}
      />
    );
  }

  return (
    <div className="tool-panel">
      <div className="tool-header">
        <div>
          <h2>🃏 Flashcards</h2>
          <p>
            Terms and definitions from: <strong>{scopeLabel}</strong>
          </p>
        </div>
        <div className="tool-controls">
          <label>
            Cards
            <input
              type="number"
              min={1}
              max={30}
              value={numCards}
              onChange={(event) => {
                const value = Number(event.target.value);
                setNumCards(Number.isNaN(value) ? 10 : Math.min(30, Math.max(1, value)));
              }}
              className="number-input"
            />
          </label>
          {studySetId && flashcards.length > 0 && (
            <button className="ghost-btn" onClick={() => setMode("review")}>
              Start review session
            </button>
          )}
          <button
            className="tool-action-btn"
            onClick={generate}
            disabled={isGenerating || !hasDocuments}
          >
            {isGenerating ? "Generating…" : flashcards.length ? "Regenerate" : "Generate Cards"}
          </button>
        </div>
      </div>

      <SavedStrip items={saved} onOpen={openSaved} onRemove={removeSaved} label="Decks" />

      <ErrorBanner message={error} onDismiss={() => setError("")} />

      {isGenerating && <ToolLoading label={`Creating flashcards from ${scopeLabel}…`} />}

      {flashcards.length > 0 && !isGenerating && (
        <div className="flashcard-grid">
          {flashcards.map((card, index) => (
            <button
              type="button"
              key={index}
              className={`flashcard ${flipped[index] ? "flipped" : ""}`}
              onClick={() => setFlipped((prev) => ({ ...prev, [index]: !prev[index] }))}
              aria-label={`Flashcard: ${card.term}`}
            >
              <div className="flashcard-inner">
                <div className="flashcard-front">
                  <span className="card-label">TERM</span>
                  <p>{card.term}</p>
                </div>
                <div className="flashcard-back">
                  <span className="card-label">DEFINITION</span>
                  <p>{card.definition}</p>
                </div>
              </div>
            </button>
          ))}
        </div>
      )}

      {flashcards.length === 0 && !isGenerating && (
        <EmptyState icon="🃏">
          Click <strong>Generate Cards</strong> to build a revision deck. Click a card to
          flip it, then start a spaced-repetition review session.
        </EmptyState>
      )}
    </div>
  );
}
