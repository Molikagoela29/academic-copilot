export function Thinking() {
  return (
    <div className="thinking" aria-label="Working">
      <span />
      <span />
      <span />
    </div>
  );
}

export function ToolLoading({ label }) {
  return (
    <div className="tool-loading">
      <Thinking />
      <p>{label}</p>
    </div>
  );
}

export function ErrorBanner({ message, onDismiss }) {
  if (!message) return null;
  return (
    <div className="error-banner" role="alert">
      <span>{message}</span>
      {onDismiss && (
        <button onClick={onDismiss} aria-label="Dismiss error">
          ✕
        </button>
      )}
    </div>
  );
}

export function EmptyState({ icon, children }) {
  return (
    <div className="tool-empty">
      <div className="tool-empty-icon">{icon}</div>
      <p>{children}</p>
    </div>
  );
}
