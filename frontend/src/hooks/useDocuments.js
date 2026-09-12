import { useCallback, useEffect, useRef, useState } from "react";

import { api } from "../api";

const POLL_INTERVAL_MS = 1500;

/**
 * Owns the document library.
 *
 * Ingestion runs in the background on the server, so this polls while any
 * document is still processing and stops as soon as the library settles.
 */
export function useDocuments() {
  const [documents, setDocuments] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const pollTimer = useRef(null);

  const refresh = useCallback(async () => {
    try {
      const data = await api.listDocuments();
      setDocuments(data.documents ?? []);
      setError("");
      return data.documents ?? [];
    } catch (err) {
      setError(err.message);
      return [];
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    return () => clearTimeout(pollTimer.current);
  }, [refresh]);

  useEffect(() => {
    clearTimeout(pollTimer.current);
    if (documents.some((doc) => doc.status === "processing")) {
      pollTimer.current = setTimeout(refresh, POLL_INTERVAL_MS);
    }
    return () => clearTimeout(pollTimer.current);
  }, [documents, refresh]);

  const upload = useCallback(
    async (file) => {
      const result = await api.uploadDocument(file);
      await refresh();
      return result;
    },
    [refresh],
  );

  const remove = useCallback(
    async (docId) => {
      await api.deleteDocument(docId);
      await refresh();
    },
    [refresh],
  );

  const readyDocuments = documents.filter((doc) => doc.status === "ready");

  return {
    documents,
    readyDocuments,
    hasReadyDocuments: readyDocuments.length > 0,
    isLoading,
    error,
    refresh,
    upload,
    remove,
  };
}
