const BASE_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";

/** Error carrying the server's user-facing `detail` message. */
export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function toError(response) {
  let detail = `Request failed (${response.status})`;
  try {
    const body = await response.json();
    if (body?.detail) detail = body.detail;
  } catch {
    // A non-JSON error body (a proxy error page, say) leaves the default text.
  }
  return new ApiError(detail, response.status);
}

async function request(path, { method = "GET", body, signal, isForm } = {}) {
  let response;
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      method,
      headers: isForm || !body ? undefined : { "Content-Type": "application/json" },
      body: isForm ? body : body ? JSON.stringify(body) : undefined,
      signal,
    });
  } catch (error) {
    if (error.name === "AbortError") throw error;
    throw new ApiError(
      "Could not reach the Academic Copilot server. Is the backend running?",
      0,
    );
  }

  if (!response.ok) throw await toError(response);
  if (response.status === 204) return null;
  return response.json();
}

/**
 * Consume a server-sent event stream.
 *
 * `handlers` maps event names to callbacks. Errors reported by the server as an
 * `error` event are raised as an ApiError so callers handle them in one place.
 */
async function stream(path, body, handlers, signal) {
  let response;
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal,
    });
  } catch (error) {
    if (error.name === "AbortError") throw error;
    throw new ApiError(
      "Could not reach the Academic Copilot server. Is the backend running?",
      0,
    );
  }

  if (!response.ok) throw await toError(response);

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let streamError = null;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    // SSE frames are separated by a blank line; keep any partial tail.
    const frames = buffer.split("\n\n");
    buffer = frames.pop() ?? "";

    for (const frame of frames) {
      let event = null;
      let data = null;
      for (const line of frame.split("\n")) {
        if (line.startsWith("event: ")) event = line.slice(7).trim();
        else if (line.startsWith("data: ")) {
          try {
            data = JSON.parse(line.slice(6));
          } catch {
            data = null;
          }
        }
      }
      if (!event) continue;
      if (event === "error") streamError = new ApiError(data?.detail ?? "Generation failed.", 500);
      else handlers[event]?.(data ?? {});
    }
  }

  if (streamError) throw streamError;
}

export const api = {
  health: () => request("/health"),

  // ── Documents ──────────────────────────────────────────────────────────
  listDocuments: () => request("/documents"),
  deleteDocument: (docId) => request(`/documents/${docId}`, { method: "DELETE" }),
  documentFileUrl: (docId, page) =>
    `${BASE_URL}/documents/${docId}/file#page=${page ?? 1}`,

  uploadDocument: (file) => {
    const formData = new FormData();
    formData.append("file", file);
    return request("/upload", { method: "POST", body: formData, isForm: true });
  },

  // ── Chat ───────────────────────────────────────────────────────────────
  ask: (payload, signal) => request("/query", { method: "POST", body: payload, signal }),
  askStream: (payload, handlers, signal) =>
    stream("/query/stream", payload, handlers, signal),

  listConversations: () => request("/conversations"),
  getConversation: (id) => request(`/conversations/${id}`),
  deleteConversation: (id) => request(`/conversations/${id}`, { method: "DELETE" }),

  // ── Agents ─────────────────────────────────────────────────────────────
  summarizeStream: (payload, handlers, signal) =>
    stream("/agents/summarize/stream", payload, handlers, signal),
  generateQuiz: (payload, signal) =>
    request("/agents/quiz", { method: "POST", body: payload, signal }),
  gradeAnswer: (payload, signal) =>
    request("/agents/quiz/grade", { method: "POST", body: payload, signal }),
  generateFlashcards: (payload, signal) =>
    request("/agents/flashcards", { method: "POST", body: payload, signal }),

  // ── Study sets & review ────────────────────────────────────────────────
  listStudySets: (kind) =>
    request(`/study-sets${kind ? `?kind=${kind}` : ""}`),
  getStudySet: (id) => request(`/study-sets/${id}`),
  deleteStudySet: (id) => request(`/study-sets/${id}`, { method: "DELETE" }),
  getDueCards: (id) => request(`/study-sets/${id}/due`),
  reviewCard: (id, payload) =>
    request(`/study-sets/${id}/review`, { method: "POST", body: payload }),
};
