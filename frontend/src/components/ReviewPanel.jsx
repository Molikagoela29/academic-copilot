import { useCallback, useEffect, useState } from "react";

import { api } from "../api";
import { ErrorBanner, ToolLoading } from "./Spinner";

const RATINGS = [
  { quality: "again", label: "Again", hint: "I forgot it", className: "rate-again" },
  { quality: "hard", label: "Hard", hint: "Struggled", className: "rate-hard" },
  { quality: "good", label: "Good", hint: "Recalled it", className: "rate-good" },
  { quality: "easy", label: "Easy", hint: "Instant", className: "rate-easy" },
];

function describeInterval(days) {
  if (days <= 0) return "later today";
  if (days === 1) return "tomorrow";
  if (days < 30) return `in ${days} days`;
  return `in ${Math.round(days / 30)} month${days >= 60 ? "s" : ""}`;
}

/**
 * Spaced-repetition review session.
 *
 * The server schedules each card with SM-2; this walks the queue of cards it
 * reports as due, one at a time.
 */
export default function ReviewPanel({ studySetId, onExit }) {
  const [queue, setQueue] = useState([]);
  const [position, setPosition] = useState(0);
  const [revealed, setRevealed] = useState(false);
  const [totalCards, setTotalCards] = useState(0);
  const [scopeLabel, setScopeLabel] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState("");
  const [reviewedCount, setReviewedCount] = useState(0);
  const [lastInterval, setLastInterval] = useState(null);

  const loadQueue = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await api.getDueCards(studySetId);
      setQueue(data.due_cards ?? []);
      setTotalCards(data.total_cards ?? 0);
      setScopeLabel(data.scope_label ?? "");
      setPosition(0);
      setRevealed(false);
      setError("");
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  }, [studySetId]);

  useEffect(() => {
    loadQueue();
  }, [loadQueue]);

  const current = queue[position];

  const rate = useCallback(
    async (quality) => {
      if (!current || isSaving) return;
      setIsSaving(true);
      try {
        const result = await api.reviewCard(studySetId, {
          card_index: current.card_index,
          quality,
        });
        setLastInterval(result.next_review_in_days);
        setReviewedCount((count) => count + 1);

        if (quality === "again") {
          // A forgotten card goes to the back of today's queue.
          setQueue((prev) => [...prev.slice(0, position), ...prev.slice(position + 1), current]);
        } else {
          setPosition((index) => index + 1);
        }
        setRevealed(false);
      } catch (err) {
        setError(err.message);
      } finally {
        setIsSaving(false);
      }
    },
    [current, isSaving, position, studySetId],
  );

  useEffect(() => {
    const onKeyDown = (event) => {
      if (event.key === " " || event.key === "Enter") {
        event.preventDefault();
        setRevealed(true);
        return;
      }
      if (!revealed) return;
      const rating = RATINGS[Number(event.key) - 1];
      if (rating) rate(rating.quality);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [revealed, rate]);

  if (isLoading) {
    return (
      <div className="tool-panel">
        <ToolLoading label="Loading your review queue…" />
      </div>
    );
  }

  const isFinished = !current;

  return (
    <div className="tool-panel">
      <div className="tool-header">
        <div>
          <h2>🔁 Review Session</h2>
          <p>
            {scopeLabel} · {totalCards} card{totalCards === 1 ? "" : "s"} in this deck
          </p>
        </div>
        <div className="tool-controls">
          <button className="ghost-btn" onClick={onExit}>
            Back to deck
          </button>
        </div>
      </div>

      <ErrorBanner message={error} onDismiss={() => setError("")} />

      {isFinished ? (
        <div className="review-done">
          <div className="tool-empty-icon">🎉</div>
          <h3>All caught up</h3>
          <p>
            {reviewedCount > 0
              ? `You reviewed ${reviewedCount} card${reviewedCount === 1 ? "" : "s"}. ` +
                (lastInterval !== null
                  ? `The last one comes back ${describeInterval(lastInterval)}.`
                  : "")
              : "Nothing is due right now. Come back when cards are scheduled again."}
          </p>
          <div className="review-done-actions">
            <button className="tool-action-btn" onClick={loadQueue}>
              Check again
            </button>
            <button className="ghost-btn" onClick={onExit}>
              Back to deck
            </button>
          </div>
        </div>
      ) : (
        <>
          <div className="review-progress">
            <div
              className="review-progress-bar"
              style={{
                width: `${(position / Math.max(queue.length, 1)) * 100}%`,
              }}
            />
            <span>
              {position + 1} of {queue.length} due
            </span>
          </div>

          <div className="review-card">
            <span className="card-label">TERM</span>
            <h3>{current.term}</h3>

            {revealed ? (
              <div className="review-definition">
                <span className="card-label">DEFINITION</span>
                <p>{current.definition}</p>
              </div>
            ) : (
              <button className="tool-action-btn" onClick={() => setRevealed(true)}>
                Show answer <kbd>Space</kbd>
              </button>
            )}
          </div>

          {revealed && (
            <div className="rating-row">
              {RATINGS.map((rating, index) => (
                <button
                  key={rating.quality}
                  className={`rating-btn ${rating.className}`}
                  onClick={() => rate(rating.quality)}
                  disabled={isSaving}
                >
                  <strong>{rating.label}</strong>
                  <span>{rating.hint}</span>
                  <kbd>{index + 1}</kbd>
                </button>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
