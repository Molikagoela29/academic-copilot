import { useEffect, useRef, useState } from "react";
import "./App.css";

const API = "http://127.0.0.1:8000";

// ─── Tab IDs ───────────────────────────────────────────────────────────────
const TABS = {
  CHAT: "chat",
  SUMMARY: "summary",
  QUIZ: "quiz",
  FLASHCARDS: "flashcards",
};

function App() {
  const fileInputRef = useRef(null);
  const messagesEndRef = useRef(null);

  // ── Upload state
  const [uploadedFile, setUploadedFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");

  // ── Active tab
  const [activeTab, setActiveTab] = useState(TABS.CHAT);

  // ── Chat state
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]);
  const [isAsking, setIsAsking] = useState(false);
  const [queryError, setQueryError] = useState("");

  // ── Summary state
  const [summary, setSummary] = useState("");
  const [isSummarizing, setIsSummarizing] = useState(false);
  const [summaryError, setSummaryError] = useState("");

  // ── Quiz state
  const [quizQuestions, setQuizQuestions] = useState([]);
  const [numQuestions, setNumQuestions] = useState(5);
  const [isGeneratingQuiz, setIsGeneratingQuiz] = useState(false);
  const [quizError, setQuizError] = useState("");
  const [revealedAnswers, setRevealedAnswers] = useState({});

  // ── Flashcard state
  const [flashcards, setFlashcards] = useState([]);
  const [numCards, setNumCards] = useState(10);
  const [isGeneratingCards, setIsGeneratingCards] = useState(false);
  const [flashcardError, setFlashcardError] = useState("");
  const [flippedCards, setFlippedCards] = useState({});

  // ─────────────────────────────────────────────────────────────────────────
  // Upload PDF
  // ─────────────────────────────────────────────────────────────────────────
  const handleUploadClick = () => fileInputRef.current.click();

  const handleFileChange = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    if (
      file.type !== "application/pdf" &&
      !file.name.toLowerCase().endsWith(".pdf")
    ) {
      setUploadError("Please select a PDF file.");
      return;
    }

    setIsUploading(true);
    setUploadError("");
    setQueryError("");

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch(`${API}/upload`, {
        method: "POST",
        body: formData,
      });
      const data = await response.json();
      if (!response.ok || data.error) throw new Error(data.error || "Failed to upload PDF.");

      setUploadedFile({
        name: data.filename,
        pages: data.pages_processed,
        chunks: data.chunks_created,
      });

      // Reset all tool outputs when a new PDF is loaded
      setMessages([]);
      setQuestion("");
      setSummary("");
      setQuizQuestions([]);
      setFlashcards([]);
      setRevealedAnswers({});
      setFlippedCards({});
      setActiveTab(TABS.CHAT);
    } catch (error) {
      setUploadError(error.message);
    } finally {
      setIsUploading(false);
      event.target.value = "";
    }
  };

  // ─────────────────────────────────────────────────────────────────────────
  // Chat
  // ─────────────────────────────────────────────────────────────────────────
  const handleAskQuestion = async () => {
    const trimmed = question.trim();
    if (!trimmed) return;
    if (!uploadedFile) { setQueryError("Please upload a PDF first."); return; }

    const userMessage = { id: Date.now(), role: "user", text: trimmed };
    setMessages((prev) => [...prev, userMessage]);
    setQuestion("");
    setIsAsking(true);
    setQueryError("");

    try {
      const response = await fetch(`${API}/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: trimmed }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error("Failed to get an answer.");

      const assistantMessage = {
        id: Date.now() + 1,
        role: "assistant",
        text:
          data.answer === "Not found."
            ? "I couldn't find relevant information about that in the uploaded study material."
            : data.answer,
        sources: data.sources || [],
        notFound: data.answer === "Not found.",
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      setQueryError(error.message);
    } finally {
      setIsAsking(false);
    }
  };

  const handleKeyDown = (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (!isAsking) handleAskQuestion();
    }
  };

  const handleSuggestion = (text) => setQuestion(text);
  const handleClearChat = () => {
    setMessages([]);
    setQuestion("");
    setQueryError("");
  };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isAsking]);

  // ─────────────────────────────────────────────────────────────────────────
  // Summary
  // ─────────────────────────────────────────────────────────────────────────
  const handleSummarize = async () => {
    if (!uploadedFile) return;
    setIsSummarizing(true);
    setSummaryError("");
    setSummary("");

    try {
      const response = await fetch(`${API}/agents/summarize`, { method: "POST" });
      const data = await response.json();
      if (!response.ok) throw new Error("Failed to generate summary.");
      setSummary(data.summary);
    } catch (error) {
      setSummaryError(error.message);
    } finally {
      setIsSummarizing(false);
    }
  };

  // ─────────────────────────────────────────────────────────────────────────
  // Quiz
  // ─────────────────────────────────────────────────────────────────────────
  const handleGenerateQuiz = async () => {
    if (!uploadedFile) return;
    setIsGeneratingQuiz(true);
    setQuizError("");
    setQuizQuestions([]);
    setRevealedAnswers({});

    try {
      const response = await fetch(`${API}/agents/quiz`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ num_questions: numQuestions }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error("Failed to generate quiz.");
      setQuizQuestions(data.questions || []);
    } catch (error) {
      setQuizError(error.message);
    } finally {
      setIsGeneratingQuiz(false);
    }
  };

  const toggleAnswer = (index) =>
    setRevealedAnswers((prev) => ({ ...prev, [index]: !prev[index] }));

  // ─────────────────────────────────────────────────────────────────────────
  // Flashcards
  // ─────────────────────────────────────────────────────────────────────────
  const handleGenerateFlashcards = async () => {
    if (!uploadedFile) return;
    setIsGeneratingCards(true);
    setFlashcardError("");
    setFlashcards([]);
    setFlippedCards({});

    try {
      const response = await fetch(`${API}/agents/flashcards`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ num_cards: numCards }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error("Failed to generate flashcards.");
      setFlashcards(data.flashcards || []);
    } catch (error) {
      setFlashcardError(error.message);
    } finally {
      setIsGeneratingCards(false);
    }
  };

  const toggleFlip = (index) =>
    setFlippedCards((prev) => ({ ...prev, [index]: !prev[index] }));

  // ─────────────────────────────────────────────────────────────────────────
  // Render
  // ─────────────────────────────────────────────────────────────────────────
  return (
    <div className="app">
      {/* ========================= SIDEBAR ========================== */}
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon">🎓</div>
          <div>
            <h1>Academic Copilot</h1>
            <p>Study smarter with your notes</p>
          </div>
        </div>

        <div className="upload-card">
          <h3>Study Material</h3>
          <p>Upload a PDF to start asking questions.</p>

          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,application/pdf"
            onChange={handleFileChange}
            style={{ display: "none" }}
          />

          <button
            className="upload-btn"
            onClick={handleUploadClick}
            disabled={isUploading}
          >
            {isUploading ? "Processing PDF..." : "+ Upload PDF"}
          </button>

          {uploadError && <p className="upload-error">{uploadError}</p>}
        </div>

        <div className="document-section">
          <p className="section-title">UPLOADED DOCUMENT</p>
          <div className="document-card">
            <div className="pdf-icon">PDF</div>
            <div className="document-info">
              {uploadedFile ? (
                <>
                  <p title={uploadedFile.name}>{uploadedFile.name}</p>
                  <span>
                    {uploadedFile.pages} pages · {uploadedFile.chunks} chunks
                  </span>
                </>
              ) : (
                <>
                  <p>No document uploaded</p>
                  <span>Your PDF will appear here</span>
                </>
              )}
            </div>
          </div>
        </div>

        <div className="sidebar-footer">
          <p>Powered by RAG + Llama</p>
        </div>
      </aside>

      {/* ========================= MAIN AREA ========================== */}
      <main className="chat-area">
        {/* ── Tab Bar ── */}
        <div className="tab-bar">
          {[
            { id: TABS.CHAT, label: "💬 Chat" },
            { id: TABS.SUMMARY, label: "📄 Summary" },
            { id: TABS.QUIZ, label: "🧠 Quiz" },
            { id: TABS.FLASHCARDS, label: "🃏 Flashcards" },
          ].map((tab) => (
            <button
              key={tab.id}
              className={`tab-btn ${activeTab === tab.id ? "tab-active" : ""}`}
              onClick={() => setActiveTab(tab.id)}
              disabled={!uploadedFile && tab.id !== TABS.CHAT}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* ========================= CHAT TAB ========================== */}
        {activeTab === TABS.CHAT && (
          <>
            <header className="chat-header">
              <div>
                <h2>AI Study Assistant</h2>
                <p>Ask questions from your uploaded study material</p>
              </div>
              <div className="header-actions">
                {messages.length > 0 && (
                  <button
                    className="clear-chat-btn"
                    onClick={handleClearChat}
                    disabled={isAsking}
                  >
                    Clear Chat
                  </button>
                )}
                <div className="status">
                  <span className="status-dot"></span>
                  {isAsking ? "Thinking..." : "Ready"}
                </div>
              </div>
            </header>

            <section className="chat-content">
              {messages.length === 0 ? (
                <div className="welcome">
                  <div className="welcome-icon">✨</div>
                  <h2>What would you like to learn?</h2>
                  <p>
                    Upload your study material and ask questions, request
                    explanations, compare concepts, or simplify difficult topics.
                  </p>
                  <div className="suggestions">
                    <button onClick={() => handleSuggestion("Explain this topic in simple words.")}>
                      Explain this topic simply
                    </button>
                    <button onClick={() => handleSuggestion("Give me an easy example of this concept.")}>
                      Give me an example
                    </button>
                    <button onClick={() => handleSuggestion("Compare these two concepts and explain their differences.")}>
                      Compare two concepts
                    </button>
                  </div>
                </div>
              ) : (
                <div className="messages-container">
                  {messages.map((message) => (
                    <div
                      key={message.id}
                      className={`message-row ${
                        message.role === "user" ? "user-row" : "assistant-row"
                      }`}
                    >
                      <div
                        className={`message-bubble ${
                          message.role === "user"
                            ? "user-message"
                            : "assistant-message"
                        }`}
                      >
                        {message.role === "assistant" && (
                          <div className="assistant-label">
                            <span className="assistant-avatar">🎓</span>
                            <span>Academic Copilot</span>
                          </div>
                        )}
                        <p className="message-text">{message.text}</p>
                        {message.role === "assistant" &&
                          message.sources &&
                          message.sources.length > 0 && (
                            <div className="sources">
                              <p className="sources-title">Sources</p>
                              <div className="source-list">
                                {message.sources.map((source, index) => (
                                  <span
                                    key={`${source.filename}-${source.page}-${index}`}
                                    className="source-chip"
                                  >
                                    📄 {source.filename} · Page {source.page}
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}
                        {message.notFound && (
                          <p className="not-found-note">
                            Try asking about a concept covered in your uploaded notes.
                          </p>
                        )}
                      </div>
                    </div>
                  ))}

                  {isAsking && (
                    <div className="message-row assistant-row">
                      <div className="message-bubble assistant-message">
                        <div className="assistant-label">
                          <span className="assistant-avatar">🎓</span>
                          <span>Academic Copilot</span>
                        </div>
                        <div className="thinking">
                          <span></span>
                          <span></span>
                          <span></span>
                        </div>
                      </div>
                    </div>
                  )}
                  <div ref={messagesEndRef} />
                </div>
              )}
            </section>

            {queryError && <div className="query-error">{queryError}</div>}

            <div className="chat-input-wrapper">
              <div className={`chat-input ${!uploadedFile ? "disabled-input" : ""}`}>
                <input
                  type="text"
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  onKeyDown={handleKeyDown}
                  disabled={!uploadedFile || isAsking}
                  placeholder={
                    uploadedFile
                      ? "Ask something about your study material..."
                      : "Upload a PDF to start asking questions..."
                  }
                />
                <button
                  className="send-btn"
                  onClick={handleAskQuestion}
                  disabled={!uploadedFile || isAsking || !question.trim()}
                >
                  ➜
                </button>
              </div>
              <p className="input-note">Answers are based on your uploaded study material.</p>
            </div>
          </>
        )}

        {/* ========================= SUMMARY TAB ========================== */}
        {activeTab === TABS.SUMMARY && (
          <div className="tool-panel">
            <div className="tool-header">
              <div>
                <h2>📄 Document Summary</h2>
                <p>Get a structured overview of your entire study material.</p>
              </div>
              <button
                className="tool-action-btn"
                onClick={handleSummarize}
                disabled={isSummarizing || !uploadedFile}
              >
                {isSummarizing ? "Summarizing..." : summary ? "Regenerate" : "Generate Summary"}
              </button>
            </div>

            {summaryError && <div className="query-error">{summaryError}</div>}

            {isSummarizing && (
              <div className="tool-loading">
                <div className="thinking"><span></span><span></span><span></span></div>
                <p>Reading through your document…</p>
              </div>
            )}

            {summary && !isSummarizing && (
              <div className="summary-content">
                <p>{summary}</p>
              </div>
            )}

            {!summary && !isSummarizing && (
              <div className="tool-empty">
                <div className="tool-empty-icon">📄</div>
                <p>Click <strong>Generate Summary</strong> to get an AI-written overview of your study material.</p>
              </div>
            )}
          </div>
        )}

        {/* ========================= QUIZ TAB ========================== */}
        {activeTab === TABS.QUIZ && (
          <div className="tool-panel">
            <div className="tool-header">
              <div>
                <h2>🧠 Quiz</h2>
                <p>Test your understanding with open-ended conceptual questions.</p>
              </div>
              <div className="tool-controls">
                <label>
                  Questions
                  <input
                    type="number"
                    min={1}
                    max={15}
                    value={numQuestions}
                    onChange={(e) => setNumQuestions(Number(e.target.value))}
                    className="number-input"
                  />
                </label>
                <button
                  className="tool-action-btn"
                  onClick={handleGenerateQuiz}
                  disabled={isGeneratingQuiz || !uploadedFile}
                >
                  {isGeneratingQuiz ? "Generating..." : quizQuestions.length ? "Regenerate" : "Generate Quiz"}
                </button>
              </div>
            </div>

            {quizError && <div className="query-error">{quizError}</div>}

            {isGeneratingQuiz && (
              <div className="tool-loading">
                <div className="thinking"><span></span><span></span><span></span></div>
                <p>Crafting questions from your study material…</p>
              </div>
            )}

            {quizQuestions.length > 0 && !isGeneratingQuiz && (
              <div className="quiz-list">
                {quizQuestions.map((q, index) => (
                  <div key={index} className="quiz-card">
                    <div className="quiz-question">
                      <span className="quiz-num">Q{index + 1}</span>
                      <p>{q.question}</p>
                    </div>
                    <button
                      className={`reveal-btn ${revealedAnswers[index] ? "revealed" : ""}`}
                      onClick={() => toggleAnswer(index)}
                    >
                      {revealedAnswers[index] ? "Hide Answer ▲" : "Reveal Answer ▼"}
                    </button>
                    {revealedAnswers[index] && (
                      <div className="quiz-answer">
                        <p>{q.answer}</p>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}

            {quizQuestions.length === 0 && !isGeneratingQuiz && (
              <div className="tool-empty">
                <div className="tool-empty-icon">🧠</div>
                <p>Click <strong>Generate Quiz</strong> to create conceptual questions from your material.</p>
              </div>
            )}
          </div>
        )}

        {/* ========================= FLASHCARDS TAB ========================== */}
        {activeTab === TABS.FLASHCARDS && (
          <div className="tool-panel">
            <div className="tool-header">
              <div>
                <h2>🃏 Flashcards</h2>
                <p>Flip cards to drill key terms and definitions.</p>
              </div>
              <div className="tool-controls">
                <label>
                  Cards
                  <input
                    type="number"
                    min={1}
                    max={20}
                    value={numCards}
                    onChange={(e) => setNumCards(Number(e.target.value))}
                    className="number-input"
                  />
                </label>
                <button
                  className="tool-action-btn"
                  onClick={handleGenerateFlashcards}
                  disabled={isGeneratingCards || !uploadedFile}
                >
                  {isGeneratingCards ? "Generating..." : flashcards.length ? "Regenerate" : "Generate Cards"}
                </button>
              </div>
            </div>

            {flashcardError && <div className="query-error">{flashcardError}</div>}

            {isGeneratingCards && (
              <div className="tool-loading">
                <div className="thinking"><span></span><span></span><span></span></div>
                <p>Creating flashcards from your study material…</p>
              </div>
            )}

            {flashcards.length > 0 && !isGeneratingCards && (
              <div className="flashcard-grid">
                {flashcards.map((card, index) => (
                  <div
                    key={index}
                    className={`flashcard ${flippedCards[index] ? "flipped" : ""}`}
                    onClick={() => toggleFlip(index)}
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
                  </div>
                ))}
              </div>
            )}

            {flashcards.length === 0 && !isGeneratingCards && (
              <div className="tool-empty">
                <div className="tool-empty-icon">🃏</div>
                <p>Click <strong>Generate Cards</strong> to create revision flashcards. Click any card to flip it.</p>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}

export default App;