import { useCallback, useEffect, useRef, useState } from "react";

import { api } from "../api";
import Markdown from "./Markdown";
import { ErrorBanner, Thinking } from "./Spinner";

const SUGGESTIONS = [
  "Explain this topic in simple words.",
  "Give me an easy example of this concept.",
  "Compare these two concepts and explain their differences.",
];

const NOT_FOUND_TEXT =
  "I couldn't find relevant information about that in the uploaded study material.";

export default function ChatPanel({
  scopeLabel,
  docId,
  hasDocuments,
  onOpenSource,
}) {
  const [conversations, setConversations] = useState([]);
  const [conversationId, setConversationId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState("");
  const [isAsking, setIsAsking] = useState(false);
  const [streamingText, setStreamingText] = useState("");
  const [streamingSources, setStreamingSources] = useState([]);
  const [error, setError] = useState("");
  const [showHistory, setShowHistory] = useState(false);

  const endRef = useRef(null);
  const abortRef = useRef(null);

  const refreshConversations = useCallback(async () => {
    try {
      const data = await api.listConversations();
      setConversations(data.conversations ?? []);
    } catch {
      // History is non-essential; the chat itself still works without it.
    }
  }, []);

  useEffect(() => {
    refreshConversations();
  }, [refreshConversations]);

  // Abort any in-flight generation when the panel unmounts.
  useEffect(() => () => abortRef.current?.abort(), []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingText, isAsking]);

  const loadConversation = async (id) => {
    try {
      const conversation = await api.getConversation(id);
      setConversationId(id);
      setMessages(
        conversation.messages.map((message) => ({
          id: message.id,
          role: message.role,
          text: message.content,
          sources: message.sources ?? [],
          notFound: message.content === "Not found.",
        })),
      );
      setShowHistory(false);
      setError("");
    } catch (err) {
      setError(err.message);
    }
  };

  const startNewChat = () => {
    abortRef.current?.abort();
    setConversationId(null);
    setMessages([]);
    setStreamingText("");
    setStreamingSources([]);
    setQuestion("");
    setError("");
  };

  const deleteConversation = async (event, id) => {
    event.stopPropagation();
    try {
      await api.deleteConversation(id);
      if (id === conversationId) startNewChat();
      await refreshConversations();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleAsk = async () => {
    const trimmed = question.trim();
    if (!trimmed || isAsking) return;
    if (!hasDocuments) {
      setError("Upload a PDF before asking questions.");
      return;
    }

    const controller = new AbortController();
    abortRef.current = controller;

    setMessages((prev) => [
      ...prev,
      { id: `local-${Date.now()}`, role: "user", text: trimmed },
    ]);
    setQuestion("");
    setIsAsking(true);
    setError("");
    setStreamingText("");
    setStreamingSources([]);

    let accumulated = "";

    try {
      await api.askStream(
        {
          question: trimmed,
          doc_id: docId,
          conversation_id: conversationId,
        },
        {
          meta: (data) => {
            setConversationId(data.conversation_id);
            setStreamingSources(data.sources ?? []);
          },
          token: (data) => {
            accumulated += data.text;
            setStreamingText(accumulated);
          },
          done: (data) => {
            const notFound = data.answer === "Not found.";
            setMessages((prev) => [
              ...prev,
              {
                id: `assistant-${Date.now()}`,
                role: "assistant",
                text: notFound ? NOT_FOUND_TEXT : data.answer,
                sources: data.sources ?? [],
                notFound,
              },
            ]);
          },
        },
        controller.signal,
      );
      refreshConversations();
    } catch (err) {
      if (err.name !== "AbortError") setError(err.message);
    } finally {
      setIsAsking(false);
      setStreamingText("");
      setStreamingSources([]);
      abortRef.current = null;
    }
  };

  const handleKeyDown = (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleAsk();
    }
  };

  return (
    <>
      <header className="chat-header">
        <div>
          <h2>AI Study Assistant</h2>
          <p>
            {hasDocuments
              ? `Asking questions against ${scopeLabel}`
              : "Upload your study material to begin"}
          </p>
        </div>
        <div className="header-actions">
          <button
            className="ghost-btn"
            onClick={() => setShowHistory((open) => !open)}
          >
            History ({conversations.length})
          </button>
          {(messages.length > 0 || conversationId) && (
            <button className="ghost-btn" onClick={startNewChat}>
              New Chat
            </button>
          )}
          {isAsking && (
            <button className="ghost-btn" onClick={() => abortRef.current?.abort()}>
              Stop
            </button>
          )}
          <div className="status">
            <span className={`status-dot ${isAsking ? "busy" : ""}`} />
            {isAsking ? "Generating…" : "Ready"}
          </div>
        </div>
      </header>

      {showHistory && (
        <div className="history-drawer">
          {conversations.length === 0 && <p className="history-empty">No saved chats yet.</p>}
          {conversations.map((conversation) => (
            <div className="history-row" key={conversation.id}>
              <button
                type="button"
                className={`history-item ${
                  conversation.id === conversationId ? "history-active" : ""
                }`}
                onClick={() => loadConversation(conversation.id)}
              >
                <span className="history-title">{conversation.title}</span>
                <span className="history-meta">
                  {conversation.message_count} messages
                </span>
              </button>
              <button
                type="button"
                className="history-delete"
                aria-label={`Delete chat: ${conversation.title}`}
                onClick={(event) => deleteConversation(event, conversation.id)}
              >
                ✕
              </button>
            </div>
          ))}
        </div>
      )}

      <section className="chat-content">
        {messages.length === 0 && !isAsking ? (
          <div className="welcome">
            <div className="welcome-icon">✨</div>
            <h2>What would you like to learn?</h2>
            <p>
              {hasDocuments
                ? `Currently searching ${scopeLabel}. Ask questions, compare concepts, or request step-by-step explanations.`
                : "Upload study materials on the left, then ask questions or generate summaries, quizzes and flashcards."}
            </p>
            <div className="suggestions">
              {SUGGESTIONS.map((suggestion) => (
                <button key={suggestion} onClick={() => setQuestion(suggestion)}>
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="messages-container">
            {messages.map((message) => (
              <MessageBubble
                key={message.id}
                message={message}
                onOpenSource={onOpenSource}
              />
            ))}

            {isAsking && (
              <div className="message-row assistant-row">
                <div className="message-bubble assistant-message">
                  <div className="assistant-label">
                    <span className="assistant-avatar">🎓</span>
                    <span>Academic Copilot</span>
                  </div>
                  {streamingText ? (
                    <Markdown>{streamingText}</Markdown>
                  ) : (
                    <Thinking />
                  )}
                  <SourceChips sources={streamingSources} onOpenSource={onOpenSource} />
                </div>
              </div>
            )}
            <div ref={endRef} />
          </div>
        )}
      </section>

      <ErrorBanner message={error} onDismiss={() => setError("")} />

      <div className="chat-input-wrapper">
        <div className={`chat-input ${!hasDocuments ? "disabled-input" : ""}`}>
          <input
            type="text"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            onKeyDown={handleKeyDown}
            disabled={!hasDocuments || isAsking}
            placeholder={
              hasDocuments
                ? `Ask something about ${scopeLabel}…`
                : "Upload a PDF to start asking questions…"
            }
          />
          <button
            className="send-btn"
            onClick={handleAsk}
            disabled={!hasDocuments || isAsking || !question.trim()}
            aria-label="Send question"
          >
            ➜
          </button>
        </div>
        <p className="input-note">
          Answers are grounded in {scopeLabel} via semantic retrieval.
        </p>
      </div>
    </>
  );
}

function MessageBubble({ message, onOpenSource }) {
  const isUser = message.role === "user";
  return (
    <div className={`message-row ${isUser ? "user-row" : "assistant-row"}`}>
      <div className={`message-bubble ${isUser ? "user-message" : "assistant-message"}`}>
        {!isUser && (
          <div className="assistant-label">
            <span className="assistant-avatar">🎓</span>
            <span>Academic Copilot</span>
          </div>
        )}

        {isUser ? (
          <p className="message-text">{message.text}</p>
        ) : (
          <Markdown>{message.text}</Markdown>
        )}

        {!isUser && <SourceChips sources={message.sources} onOpenSource={onOpenSource} />}

        {message.notFound && (
          <p className="not-found-note">
            Try asking about a concept covered in your uploaded notes.
          </p>
        )}
      </div>
    </div>
  );
}

function SourceChips({ sources, onOpenSource }) {
  if (!sources?.length) return null;
  return (
    <div className="sources">
      <p className="sources-title">Sources</p>
      <div className="source-list">
        {sources.map((source, index) => (
          <button
            type="button"
            key={`${source.filename}-${source.page}-${index}`}
            className="source-chip"
            onClick={() => onOpenSource(source)}
            title="Open this page in the original PDF"
          >
            📄 {source.filename} · Page {source.page}
          </button>
        ))}
      </div>
    </div>
  );
}
