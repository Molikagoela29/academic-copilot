from typing import Optional


class CopilotError(Exception):
    """Base class for application errors that map to a clean HTTP response."""

    status_code = 500
    default_message = "An unexpected error occurred."

    def __init__(self, message: Optional[str] = None):
        self.message = message or self.default_message
        super().__init__(self.message)


class DocumentNotFound(CopilotError):
    status_code = 404
    default_message = "Document not found."


class NoDocumentsIndexed(CopilotError):
    status_code = 409
    default_message = "No documents have been indexed yet. Upload a PDF first."


class DocumentNotReady(CopilotError):
    status_code = 409
    default_message = "This document is still being processed."


class InvalidUpload(CopilotError):
    status_code = 400
    default_message = "The uploaded file could not be processed."


class LLMUnavailable(CopilotError):
    status_code = 503
    default_message = (
        "Could not reach the local Llama model. Make sure Ollama is running "
        "and the configured model has been pulled."
    )


class LLMBadOutput(CopilotError):
    status_code = 502
    default_message = (
        "The model returned a response that could not be parsed. Please try again."
    )
