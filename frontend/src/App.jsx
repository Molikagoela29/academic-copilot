import { useEffect, useRef, useState } from "react";
import "./App.css";

function App() {
  const fileInputRef = useRef(null);
  const messagesEndRef = useRef(null);

  const [uploadedFile, setUploadedFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");

  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]);
  const [isAsking, setIsAsking] = useState(false);
  const [queryError, setQueryError] = useState("");

  // ---------------------------------
  // Upload PDF
  // ---------------------------------
  const handleUploadClick = () => {
    fileInputRef.current.click();
  };

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
      const response = await fetch("http://127.0.0.1:8000/upload", {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (!response.ok || data.error) {
        throw new Error(data.error || "Failed to upload PDF.");
      }

      setUploadedFile({
        name: data.filename,
        pages: data.pages_processed,
        chunks: data.chunks_created,
      });

      // Start fresh when a new PDF is uploaded
      setMessages([]);
      setQuestion("");
    } catch (error) {
      setUploadError(error.message);
    } finally {
      setIsUploading(false);

      // Allows same PDF to be selected again later
      event.target.value = "";
    }
  };

  // ---------------------------------
  // Ask question
  // ---------------------------------
  const handleAskQuestion = async () => {
    const trimmedQuestion = question.trim();

    if (!trimmedQuestion) return;

    if (!uploadedFile) {
      setQueryError("Please upload a PDF first.");
      return;
    }

    const userMessage = {
      id: Date.now(),
      role: "user",
      text: trimmedQuestion,
    };

    setMessages((previous) => [...previous, userMessage]);
    setQuestion("");
    setIsAsking(true);
    setQueryError("");

    try {
      const response = await fetch("http://127.0.0.1:8000/query", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          question: trimmedQuestion,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error("Failed to get an answer.");
      }

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

      setMessages((previous) => [...previous, assistantMessage]);
    } catch (error) {
      setQueryError(error.message);
    } finally {
      setIsAsking(false);
    }
  };

  // ---------------------------------
  // Enter key
  // ---------------------------------
  const handleKeyDown = (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();

      if (!isAsking) {
        handleAskQuestion();
      }
    }
  };

  // ---------------------------------
  // Suggestion buttons
  // ---------------------------------
  const handleSuggestion = (text) => {
    setQuestion(text);
  };

  const handleClearChat = () => {
        setMessages([]);
        setQuestion("");
        setQueryError("");
      };

      useEffect(() => {
        messagesEndRef.current?.scrollIntoView({
          behavior: "smooth",
        });
      }, [messages, isAsking]);

  return (
    <div className="app">
      {/* =========================
          SIDEBAR
      ========================== */}
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

          {uploadError && (
            <p className="upload-error">
              {uploadError}
            </p>
          )}
        </div>

        <div className="document-section">
          <p className="section-title">
            UPLOADED DOCUMENT
          </p>

          <div className="document-card">
            <div className="pdf-icon">
              PDF
            </div>

            <div className="document-info">
              {uploadedFile ? (
                <>
                  <p title={uploadedFile.name}>
                    {uploadedFile.name}
                  </p>

                  <span>
                    {uploadedFile.pages} pages ·{" "}
                    {uploadedFile.chunks} chunks
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

      {/* =========================
          CHAT AREA
      ========================== */}
      <main className="chat-area">
        <header className="chat-header">
          <div>
            <h2>AI Study Assistant</h2>

            <p>
              Ask questions from your uploaded study material
            </p>
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

        {/* =========================
            CHAT CONTENT
        ========================== */}
        <section className="chat-content">
          {messages.length === 0 ? (
            <div className="welcome">
              <div className="welcome-icon">
                ✨
              </div>

              <h2>
                What would you like to learn?
              </h2>

              <p>
                Upload your study material and ask questions,
                request explanations, compare concepts, or
                simplify difficult topics.
              </p>

              <div className="suggestions">
                <button
                  onClick={() =>
                    handleSuggestion(
                      "Explain this topic in simple words."
                    )
                  }
                >
                  Explain this topic simply
                </button>

                <button
                  onClick={() =>
                    handleSuggestion(
                      "Give me an easy example of this concept."
                    )
                  }
                >
                  Give me an example
                </button>

                <button
                  onClick={() =>
                    handleSuggestion(
                      "Compare these two concepts and explain their differences."
                    )
                  }
                >
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
                    message.role === "user"
                      ? "user-row"
                      : "assistant-row"
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
                        <span className="assistant-avatar">
                          🎓
                        </span>

                        <span>
                          Academic Copilot
                        </span>
                      </div>
                    )}

                    <p className="message-text">
                      {message.text}
                    </p>

                    {message.role === "assistant" &&
                      message.sources &&
                      message.sources.length > 0 && (
                        <div className="sources">
                          <p className="sources-title">
                            Sources
                          </p>

                          <div className="source-list">
                            {message.sources.map(
                              (source, index) => (
                                <span
                                  key={`${source.filename}-${source.page}-${index}`}
                                  className="source-chip"
                                >
                                  📄 {source.filename} · Page{" "}
                                  {source.page}
                                </span>
                              )
                            )}
                          </div>
                        </div>
                      )}

                    {message.notFound && (
                      <p className="not-found-note">
                        Try asking about a concept covered in
                        your uploaded notes.
                      </p>
                    )}
                  </div>
                </div>
              ))}

              {isAsking && (
                <div className="message-row assistant-row">
                  <div className="message-bubble assistant-message">
                    <div className="assistant-label">
                      <span className="assistant-avatar">
                        🎓
                      </span>

                      <span>
                        Academic Copilot
                      </span>
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

        {/* =========================
            QUERY ERROR
        ========================== */}
        {queryError && (
          <div className="query-error">
            {queryError}
          </div>
        )}

        {/* =========================
            INPUT AREA
        ========================== */}
        <div className="chat-input-wrapper">
          <div
            className={`chat-input ${
              !uploadedFile ? "disabled-input" : ""
            }`}
          >
            <input
              type="text"
              value={question}
              onChange={(event) =>
                setQuestion(event.target.value)
              }
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
              disabled={
                !uploadedFile ||
                isAsking ||
                !question.trim()
              }
            >
              ➜
            </button>
          </div>

          <p className="input-note">
            Answers are based on your uploaded study material.
          </p>
        </div>
      </main>
    </div>
  );
}

export default App;