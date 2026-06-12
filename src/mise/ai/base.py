"""Base classes and models for AI providers."""

from abc import ABC, abstractmethod
from typing import Optional

from pydantic import BaseModel


class AIMessage(BaseModel):
    """A single message in an AI conversation."""

    role: str  # "system", "user", or "assistant"
    content: str


class AIResponse(BaseModel):
    """A response from an AI provider."""

    content: str
    model: str
    provider: str
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None

    def __str__(self) -> str:
        return self.content


class BaseAIProvider(ABC):
    """Abstract base class for all AI providers.

    Subclass this and implement the required methods to add a new provider.
    Register the subclass with :class:`AIProviderRegistry` so the CLI can
    find it.
    """

    name: str = "unknown"
    default_model: str = ""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        model: Optional[str] = None,
    ) -> AIResponse:
        """Send a single prompt and return the AI response.

        Parameters
        ----------
        prompt : str
            The user prompt.
        system : str, optional
            System-level instructions.
        model : str, optional
            Model override (uses default_model if not given).

        Returns
        -------
        AIResponse
        """

    @abstractmethod
    def chat(
        self,
        messages: list[AIMessage],
        model: Optional[str] = None,
    ) -> AIResponse:
        """Send a multi-turn conversation and return the AI response.

        Parameters
        ----------
        messages : list[AIMessage]
            Conversation history.
        model : str, optional
            Model override.

        Returns
        -------
        AIResponse
        """

    @abstractmethod
    def health_check(self) -> bool:
        """Return True if the provider is reachable and ready to use."""