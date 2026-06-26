"""Provider-agnostic LLM interface.

Every provider implements .complete(prompt, system) -> str.
Pick the active one with LLM_PROVIDER in .env (gemini | ollama | mock).
This keeps Phase 3 (extraction, summaries, chatbot) decoupled from any vendor.
"""
from __future__ import annotations
from abc import ABC, abstractmethod


class LLMProvider(ABC):
    @abstractmethod
    def complete(self, prompt: str, system: str | None = None) -> str:
        ...
