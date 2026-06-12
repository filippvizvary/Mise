"""Mise AI module – pluggable AI providers for discount analysis.

Importing this module automatically registers all built-in providers
with the global :data:`ai_registry`.
"""

from mise.ai.base import AIMessage, AIResponse, BaseAIProvider
from mise.ai.registry import ai_registry

# ── Register built-in providers ──────────────────────────────────────
from mise.ai.ollama import OllamaProvider   # noqa: E402, F401
from mise.ai.openai import OpenAIProvider   # noqa: E402, F401

ai_registry.register("ollama", OllamaProvider, default=True)
ai_registry.register("openai", OpenAIProvider)

__all__ = [
    "AIMessage",
    "AIResponse",
    "BaseAIProvider",
    "ai_registry",
    "OllamaProvider",
    "OpenAIProvider",
]