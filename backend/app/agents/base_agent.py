from abc import ABC, abstractmethod


class BaseAgent(ABC):
    """
    Abstract base for all Academic Copilot agents.

    Subclasses implement `run()` with whatever keyword arguments
    their specific task requires.
    """

    @abstractmethod
    def run(self, **kwargs) -> dict:
        """Execute the agent task and return a structured result dict."""
        ...
