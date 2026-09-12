import { useEffect, useState } from "react";

import "./App.css";
import { api } from "./api";
import ChatPanel from "./components/ChatPanel";
import FlashcardPanel from "./components/FlashcardPanel";
import PdfViewer from "./components/PdfViewer";
import QuizPanel from "./components/QuizPanel";
import Sidebar from "./components/Sidebar";
import SummaryPanel from "./components/SummaryPanel";
import { useDocuments } from "./hooks/useDocuments";

const TABS = [
  { id: "chat", label: "💬 Chat" },
  { id: "summary", label: "📄 Summary" },
  { id: "quiz", label: "🧠 Quiz" },
  { id: "flashcards", label: "🃏 Flashcards" },
];

export default function App() {
  const {
    documents,
    readyDocuments,
    hasReadyDocuments,
    upload,
    remove,
  } = useDocuments();

  const [selectedDocId, setSelectedDocId] = useState("all");
  const [activeTab, setActiveTab] = useState("chat");
  const [openSource, setOpenSource] = useState(null);
  const [health, setHealth] = useState(null);

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth(null));
  }, []);

  // A selection can go stale when its document is deleted or is still indexing.
  // Derive the scope during render rather than correcting state in an effect,
  // which would cost an extra render pass every time the library changes.
  const selectionIsValid =
    selectedDocId === "all" ||
    readyDocuments.some((doc) => doc.doc_id === selectedDocId);
  const effectiveDocId = selectionIsValid ? selectedDocId : "all";

  const activeDocument = readyDocuments.find((doc) => doc.doc_id === effectiveDocId);
  const scopeLabel =
    effectiveDocId === "all"
      ? `All Documents (${readyDocuments.length})`
      : activeDocument?.filename ?? "Selected Document";

  // The API treats a null doc_id as "search everything".
  const docId = effectiveDocId === "all" ? null : effectiveDocId;

  const panelProps = { scopeLabel, docId, hasDocuments: hasReadyDocuments };

  return (
    <div className="app">
      <Sidebar
        documents={documents}
        readyDocuments={readyDocuments}
        selectedDocId={effectiveDocId}
        onSelectDoc={setSelectedDocId}
        onUpload={upload}
        onDelete={remove}
        health={health}
      />

      <main className="chat-area">
        <div className="top-nav-bar">
          <div className="tab-bar">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                className={`tab-btn ${activeTab === tab.id ? "tab-active" : ""}`}
                onClick={() => setActiveTab(tab.id)}
                disabled={!hasReadyDocuments && tab.id !== "chat"}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <div className="scope-pill">
            <span className="scope-tag">Scope:</span>
            <span className="scope-name" title={scopeLabel}>
              {scopeLabel}
            </span>
          </div>
        </div>

        {activeTab === "chat" && (
          <ChatPanel {...panelProps} onOpenSource={setOpenSource} />
        )}
        {activeTab === "summary" && <SummaryPanel {...panelProps} />}
        {activeTab === "quiz" && <QuizPanel {...panelProps} />}
        {activeTab === "flashcards" && <FlashcardPanel {...panelProps} />}
      </main>

      <PdfViewer source={openSource} onClose={() => setOpenSource(null)} />
    </div>
  );
}
