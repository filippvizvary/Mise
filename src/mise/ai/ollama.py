"""Ollama AI provider – LLM inference via the Ollama API (ollama.com)."""

import os
from typing import Optional

from ollama import Client

from mise.ai.base import AIMessage, AIResponse, BaseAIProvider


class OllamaProvider(BaseAIProvider):
    """AI provider that communicates with Ollama via ollama.com.

    Configuration
    -------------
    Uses the ``ollama`` Python package's ``Client`` class. By default,
    connects to ``https://ollama.com`` with an API key read from the
    ``OLLAMA_API_KEY`` environment variable.

    Parameters
    ----------
    model : str
        Default model to use (e.g. ``"gpt-oss:120b"``).
    host : str
        Ollama server URL.
    api_key : str
        Bearer token for authentication.
    """

    name = "ollama"
    default_model = "gpt-oss:120b"

    def __init__(
        self,
        model: Optional[str] = None,
        host: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> None:
        self.default_model = model or self.default_model
        self._host = host or os.environ.get("OLLAMA_HOST", "https://ollama.com")
        self._api_key = api_key or os.environ.get("OLLAMA_API_KEY", "")

    def _get_client(self) -> Client:
        """Create the Ollama client."""
        headers = {}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return Client(host=self._host, headers=headers)

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        model: Optional[str] = None,
    ) -> AIResponse:
        """Generate a response using Ollama.

        Parameters
        ----------
        prompt : str
            The user prompt.
        system : str, optional
            System prompt for context.
        model : str, optional
            Model override (uses default_model if not given).

        Returns
        -------
        AIResponse
        """
        model = model or self.default_model
        client = self._get_client()

        messages: list[dict] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = client.chat(model=model, messages=messages)

        message = response.get("message", {})
        content = message.get("content", "")

        return AIResponse(
            content=content,
            model=response.get("model", model),
            provider=self.name,
            prompt_tokens=response.get("prompt_eval_count"),
            completion_tokens=response.get("eval_count"),
        )

    def chat(
        self,
        messages: list[AIMessage],
        model: Optional[str] = None,
    ) -> AIResponse:
        """Chat with Ollama using a multi-turn conversation.

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
        model = model or self.default_model
        client = self._get_client()

        msg_dicts = [{"role": m.role, "content": m.content} for m in messages]
        response = client.chat(model=model, messages=msg_dicts)

        message = response.get("message", {})
        content = message.get("content", "")

        return AIResponse(
            content=content,
            model=response.get("model", model),
            provider=self.name,
            prompt_tokens=response.get("prompt_eval_count"),
            completion_tokens=response.get("eval_count"),
        )

    def health_check(self) -> bool:
        """Check if the Ollama server is reachable."""
        try:
            client = self._get_client()
            client.list()
            return True
        except Exception:
            return False