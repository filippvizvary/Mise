"""AI provider registry – discover and use AI providers by name."""

from __future__ import annotations

from typing import Optional, Type

from mise.ai.base import BaseAIProvider, AIResponse


class AIProviderRegistry:
    """Central registry for all AI providers.

    Usage::

        from mise.ai.registry import ai_registry

        # Register a provider
        ai_registry.register("ollama", OllamaProvider)

        # Get a provider instance
        provider = ai_registry.get("ollama")
        response = provider.generate("Hello!")

        # Use the default provider
        response = ai_registry.default().generate("Hello!")
    """

    def __init__(self) -> None:
        self._providers: dict[str, Type[BaseAIProvider]] = {}
        self._default: Optional[str] = None

    def register(
        self,
        name: str,
        provider_cls: Type[BaseAIProvider],
        default: bool = False,
    ) -> None:
        """Register a provider class under the given name.

        Parameters
        ----------
        name : str
            Unique provider name (case-insensitive).
        provider_cls : Type[BaseAIProvider]
            The provider class (will be instantiated on retrieval).
        default : bool
            If True, set this as the default provider.
        """
        key = name.lower()
        self._providers[key] = provider_cls
        if default or self._default is None:
            self._default = key

    def get(self, name: Optional[str] = None) -> BaseAIProvider:
        """Return an instance of the named provider.

        If *name* is None, returns the default provider.

        Raises KeyError if the name is not registered.
        """
        key = (name or self._default or "").lower()
        if key not in self._providers:
            available = ", ".join(self.list_available()) or "(none)"
            raise KeyError(
                f"No AI provider registered as '{name}'. Available: {available}"
            )
        return self._providers[key]()

    def default(self) -> BaseAIProvider:
        """Return an instance of the default provider."""
        return self.get(self._default)

    def list_available(self) -> list[str]:
        """Return sorted list of registered provider names."""
        return sorted(self._providers.keys())

    def set_default(self, name: str) -> None:
        """Change the default provider."""
        key = name.lower()
        if key not in self._providers:
            available = ", ".join(self.list_available()) or "(none)"
            raise KeyError(
                f"No AI provider registered as '{name}'. Available: {available}"
            )
        self._default = key


# Module-level singleton
ai_registry = AIProviderRegistry()