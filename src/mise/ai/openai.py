"""OpenAI AI provider – cloud LLM via the OpenAI API."""

from typing import Optional

from openai import OpenAI

from mise.ai.base import AIMessage, AIResponse, BaseAIProvider
from mise.config import OPENAI_API_KEY, OPENAI_BASE_URL


class OpenAIProvider(BaseAIProvider):
    """AI provider that communicates with the OpenAI API.

    Configuration
    -------------
    Uses the ``openai`` Python package. By default, connects to
    ``https://api.openai.com/v1`` with an API key read from the
    ``OPENAI_API_KEY`` environment variable.

    Parameters
    ----------
    model : str
        Default model to use (e.g. ``"gpt-4o-mini"``).
    api_key : str
        OpenAI API key for authentication.
    base_url : str
        Custom base URL (useful for Azure OpenAI or compatible APIs).
    """

    name = "openai"
    default_model = "gpt-4o-mini"

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> None:
        self.default_model = model or self.default_model
        self._api_key = api_key or OPENAI_API_KEY
        self._base_url = base_url or OPENAI_BASE_URL

    def _get_client(self) -> OpenAI:
        """Create an OpenAI client instance."""
        kwargs: dict = {}
        if self._api_key:
            kwargs["api_key"] = self._api_key
        if self._base_url:
            kwargs["base_url"] = self._base_url
        return OpenAI(**kwargs)

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        model: Optional[str] = None,
    ) -> AIResponse:
        """Generate a response using OpenAI.

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
            messages.append({"role": "developer", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = client.chat.completions.create(
            model=model,
            messages=messages,
        )

        choice = response.choices[0]
        content = choice.message.content or ""

        usage = response.usage
        return AIResponse(
            content=content,
            model=response.model,
            provider=self.name,
            prompt_tokens=usage.prompt_tokens if usage else None,
            completion_tokens=usage.completion_tokens if usage else None,
            total_tokens=usage.total_tokens if usage else None,
        )

    def chat(
        self,
        messages: list[AIMessage],
        model: Optional[str] = None,
    ) -> AIResponse:
        """Chat with OpenAI using a multi-turn conversation.

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
        response = client.chat.completions.create(
            model=model,
            messages=msg_dicts,
        )

        choice = response.choices[0]
        content = choice.message.content or ""

        usage = response.usage
        return AIResponse(
            content=content,
            model=response.model,
            provider=self.name,
            prompt_tokens=usage.prompt_tokens if usage else None,
            completion_tokens=usage.completion_tokens if usage else None,
            total_tokens=usage.total_tokens if usage else None,
        )

    def health_check(self) -> bool:
        """Check if the OpenAI API is reachable and the key is valid."""
        try:
            client = self._get_client()
            client.models.list()
            return True
        except Exception:
            return False