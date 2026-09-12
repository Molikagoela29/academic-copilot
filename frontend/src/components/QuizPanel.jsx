import { useEffect, useRef, useState } from "react";

import { api } from "../api";
import Markdown from "./Markdown";
import { EmptyState, ErrorBanner, ToolLoading } from "./Spinner";
import { SavedStrip } from "./SummaryPanel";

const VERDICT_CLASS = {
  correct: "verdict-correct",
  "partially correct": "verdict-partial",
  incorrect: "verdict-incorrect",
};

export default function QuizPanel({ scopeLabel, docId, hasDocuments }) {
  const [questions, setQuestions] = useState([]);
  const [numQuestions, setNumQuestions] = useState(5);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState("");
  const [revealed, setRevealed] = useState({});
  const [answers, setAnswers] = useState({});
  const [grades, setGrades] = useState({});
  const [gradingIndex, setGradingIndex] = useState(null);
  const [saved, setSaved] = useState([]);
  const abortRef = useRef(null);

  const refreshSaved = async () => {
    try {
      const data = await api.listStudySets("quiz");
      setSaved(data.study_sets ?? []);
    } catch {
      // Non-fatal.
    }
  };

  useEffect(() => {
    refreshSaved();
    return () => abortRef.current?.abort();
  }, []);

  const resetAttempt = () => {
    setRevealed({});
    setAnswers({});
    setGrades({});
  };

  const generate = async () => {
    const controller = new AbortController();
    abortRef.current = controller;

    setIsGenerating(true);
    setError("");
    setQuestions([]);
    resetAttempt();

    try {
      const data = await api.generateQuiz(
        { num_questions: numQuestions, doc_id: docId, save: true },
        controller.signal,
      );
      setQuestions(data.questions ?? []);
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
      setQuestions(studySet.payload ?? []);
      resetAttempt();
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

  const gradeAnswer = async (index) => {
    const studentAnswer = (answers[index] ?? "").trim();
    if (!studentAnswer) return;

    setGradingIndex(index);
    setError("");

    try {
      const grade = await api.gradeAnswer({
        question: questions[index].question,
        expected_answer: questions[index].answer,
        student_answer: studentAnswer,
      });
      setGrades((prev) => ({ ...prev, [index]: grade }));
      setRevealed((prev) => ({ ...prev, [index]: true }));
    } catch (err) {
      setError(err.message);
    } finally {
      setGradingIndex(null);
    }
  };

  const scored = Object.values(grades);
  const averageScore = scored.length
    ? Math.round(scored.reduce((sum, grade) => sum + grade.score, 0) / scored.length)
    : null;

  return (
    <div className="tool-panel">
      <div className="tool-header">
        <div>
          <h2>🧠 Conceptual Quiz</h2>
          <p>
            Questions from: <strong>{scopeLabel}</strong>
          </p>
        </div>
        <div className="tool-controls">
          <label>
            Questions
            <input
              type="number"
              min={1}
              max={15}
              value={numQuestions}
              onChange={(event) => {
                const value = Number(event.target.value);
                // An empty field yields 0; clamp so the request stays valid.
                setNumQuestions(Number.isNaN(value) ? 5 : Math.min(15, Math.max(1, value)));
              }}
              className="number-input"
            />
          </label>
          <button
            className="tool-action-btn"
            onClick={generate}
            disabled={isGenerating || !hasDocuments}
          >
            {isGenerating ? "Generating…" : questions.length ? "Regenerate" : "Generate Quiz"}
          </button>
        </div>
      </div>

      <SavedStrip items={saved} onOpen={openSaved} onRemove={removeSaved} />

      {averageScore !== null && (
        <div className="score-banner">
          Average score across {scored.length} graded answer
          {scored.length === 1 ? "" : "s"}: <strong>{averageScore}%</strong>
        </div>
      )}

      <ErrorBanner message={error} onDismiss={() => setError("")} />

      {isGenerating && <ToolLoading label={`Crafting questions from ${scopeLabel}…`} />}

      {questions.length > 0 && !isGenerating && (
        <div className="quiz-list">
          {questions.map((item, index) => {
            const grade = grades[index];
            return (
              <div key={index} className="quiz-card">
                <div className="quiz-question">
                  <span className="quiz-num">Q{index + 1}</span>
                  <p>{item.question}</p>
                </div>

                <textarea
                  className="quiz-answer-input"
                  rows={3}
                  placeholder="Write your answer, then check it…"
                  value={answers[index] ?? ""}
                  onChange={(event) =>
                    setAnswers((prev) => ({ ...prev, [index]: event.target.value }))
                  }
                  disabled={gradingIndex === index}
                />

                <div className="quiz-actions">
                  <button
                    className="tool-action-btn small"
                    onClick={() => gradeAnswer(index)}
                    disabled={!(answers[index] ?? "").trim() || gradingIndex === index}
                  >
                    {gradingIndex === index ? "Checking…" : "Check my answer"}
                  </button>
                  <button
                    className={`reveal-btn ${revealed[index] ? "revealed" : ""}`}
                    onClick={() =>
                      setRevealed((prev) => ({ ...prev, [index]: !prev[index] }))
                    }
                  >
                    {revealed[index] ? "Hide explanation ▲" : "Reveal explanation ▼"}
                  </button>
                </div>

                {grade && (
                  <div className={`grade-box ${VERDICT_CLASS[grade.verdict] ?? ""}`}>
                    <div className="grade-header">
                      <span className="grade-score">{grade.score}%</span>
                      <span className="grade-verdict">{grade.verdict}</span>
                    </div>
                    <p>{grade.feedback}</p>
                  </div>
                )}

                {revealed[index] && (
                  <div className="quiz-answer">
                    <Markdown>{item.answer}</Markdown>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {questions.length === 0 && !isGenerating && (
        <EmptyState icon="🧠">
          Click <strong>Generate Quiz</strong> to test your understanding of {scopeLabel}.
        </EmptyState>
      )}
    </div>
  );
}
