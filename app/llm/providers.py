"""Concrete LLM providers + a factory.

- GeminiProvider : Google Gemini free tier. Paces requests and retries on the
                   free-tier rate limit (HTTP 429) so bulk extraction succeeds.
- OllamaProvider : fully local models, zero cost.
- MockProvider   : deterministic stub so the pipeline runs with no key.
"""
from __future__ import annotations

import json
import re
import time
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
    """Google Gemini with free-tier friendly pacing + retry on 429.

    The free tier allows only a handful of requests per minute, so we (1) keep a
    minimum gap between calls and (2) if we still hit a 429, wait the delay the
    API suggests and retry instead of dropping the opportunity.
    """

    MIN_INTERVAL = 7.0    # seconds between calls (~8/min, under the free limit)
    MAX_RETRIES = 5

    def __init__(self):
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is empty. Add it to .env.")
        import google.generativeai as genai  # imported lazily
        genai.configure(api_key=settings.gemini_api_key)
        self._model = genai.GenerativeModel(settings.gemini_model)
        self._last_call = 0.0
        self._daily_exhausted = False

    def _throttle(self) -> None:
        wait = self.MIN_INTERVAL - (time.monotonic() - self._last_call)
        if wait > 0:
            time.sleep(wait)

    def complete(self, prompt: str, system: str | None = None) -> str:
        if self._daily_exhausted:
            raise RuntimeError("Gemini free daily quota exhausted — skipping (resets in ~24h).")
        text = prompt if not system else f"{system}\n\n{prompt}"
        for attempt in range(self.MAX_RETRIES):
            self._throttle()
            self._last_call = time.monotonic()
            try:
                resp = self._model.generate_content(text)
                return (resp.text or "").strip()
            except Exception as e:
                msg = str(e)
                low = msg.lower()
                is_rate = "429" in msg or "quota" in low or "exhausted" in low
                is_daily = "perday" in low or "requestsperday" in low
                if is_daily:
                    # daily cap won't recover for hours: stop retrying everything
                    self._daily_exhausted = True
                    raise RuntimeError("Gemini free daily quota exhausted (per-day limit). "
                                       "Re-run tomorrow, switch model/provider, or enable billing.")
                if is_rate and attempt < self.MAX_RETRIES - 1:
                    m = re.search(r"seconds:\s*(\d+)", msg)
                    back = (int(m.group(1)) + 1) if m else 20
                    time.sleep(back)
                    continue
                raise
        return ""


class GroqProvider(LLMProvider):
    """Groq free tier — OpenAI-compatible API, extremely fast inference.

    Free limits are generous (thousands of requests/day for small Llama
    models), so this is the workhorse fallback when Gemini's daily quota runs
    out. Uses stdlib urllib only — no extra pip dependency.
    """

    MIN_INTERVAL = 2.1   # free tier allows ~30 requests/min
    API_URL = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(self):
        if not settings.groq_api_key:
            raise RuntimeError("GROQ_API_KEY is empty. Add it to .env "
                               "(free key at https://console.groq.com).")
        self._last_call = 0.0

    def _throttle(self) -> None:
        wait = self.MIN_INTERVAL - (time.monotonic() - self._last_call)
        if wait > 0:
            time.sleep(wait)

    def complete(self, prompt: str, system: str | None = None) -> str:
        self._throttle()
        self._last_call = time.monotonic()
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        payload = {"model": settings.groq_model, "messages": messages,
                   "temperature": 0}
        req = urllib.request.Request(
            self.API_URL,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {settings.groq_api_key}"},
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read())
        return (data["choices"][0]["message"]["content"] or "").strip()


class FallbackProvider(LLMProvider):
    """Chain of providers: try each in order until one answers.

    A provider that reports its DAILY quota exhausted is dropped for the rest
    of the run (retrying it every row is pointless); transient errors just
    fall through to the next provider for this one call.
    """

    def __init__(self, named_providers: list[tuple[str, LLMProvider]]):
        self._providers = named_providers
        self._dead: set[str] = set()

    def complete(self, prompt: str, system: str | None = None) -> str:
        last_err: Exception | None = None
        for name, provider in self._providers:
            if name in self._dead:
                continue
            try:
                return provider.complete(prompt, system=system)
            except Exception as e:
                last_err = e
                low = str(e).lower()
                if "daily quota" in low or "per-day" in low or "perday" in low:
                    self._dead.add(name)   # dead for the rest of this run
        raise last_err or RuntimeError("No LLM provider available.")


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
    if provider == "groq":
        return GroqProvider()
    if provider == "ollama":
        return OllamaProvider()
    if provider == "auto":
        # Fallback chain: every configured provider, best-first.
        chain: list[tuple[str, LLMProvider]] = []
        if settings.gemini_api_key:
            try:
                chain.append(("gemini", GeminiProvider()))
            except Exception:
                pass
        if settings.groq_api_key:
            chain.append(("groq", GroqProvider()))
        chain.append(("ollama", OllamaProvider()))  # last resort, local
        return FallbackProvider(chain)
    return MockProvider()
