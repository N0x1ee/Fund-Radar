"""Concrete LLM providers + a factory.

- GeminiProvider : Google Gemini free tier (1500 req/day, no card).
- OllamaProvider : fully local models, zero cost.
- MockProvider   : deterministic stub so the pipeline runs with no key.
"""
from __future__ import annotations

import json
import urllib.request

from app.config import settings
from app.llm.base import LLMProvider


class MockProvider(LLMProvider):
    """No external calls. Echoes a structured-looking response for testing."""

    def complete(self, prompt: str, system: str | None = None) -> str:
        return (
            "[mock-llm] No real model configured. "
            "Set LLM_PROVIDER=gemini and GEMINI_API_KEY in .env to enable AI. "
            f"(prompt chars: {len(prompt)})"
        )


class GeminiProvider(LLMProvider):
    def __init__(self):
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is empty. Add it to .env.")
        import google.generativeai as genai  # imported lazily
        genai.configure(api_key=settings.gemini_api_key)
        self._model = genai.GenerativeModel(settings.gemini_model)

    def complete(self, prompt: str, system: str | None = None) -> str:
        text = prompt if not system else f"{system}\n\n{prompt}"
        resp = self._model.generate_content(text)
        return (resp.text or "").strip()


class OllamaProvider(LLMProvider):
    """Talks to a local Ollama server over HTTP. No pip dependency needed."""

    def complete(self, prompt: str, system: str | None = None) -> str:
        payload = {
            "model": settings.ollama_model,
            "prompt": prompt if not system else f"{system}\n\n{prompt}",
            "stream": False,
        }
        req = urllib.request.Request(
            f"{settings.ollama_host}/api/generate",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read()).get("response", "").strip()


def get_llm() -> LLMProvider:
    provider = settings.llm_provider.lower()
    if provider == "gemini":
        return GeminiProvider()
    if provider == "ollama":
        return OllamaProvider()
    return MockProvider()
