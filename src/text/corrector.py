"""Text correction using LLM (supports Groq and OpenAI)."""

from __future__ import annotations

import time
from dataclasses import dataclass

from . import prompts


@dataclass
class CorrectionResult:
    """Result of a correction call, including observability fields."""

    text: str  # final text (corrected, or original on fallback)
    corrected: bool  # True if LLM actually changed the text
    latency_ms: float  # wall-clock time of the correction step
    prompt_tokens: int = 0  # from the provider response
    completion_tokens: int = 0
    total_tokens: int = 0
    model: str = ""
    provider: str = ""
    prompt_id: str = ""
    prompt_version: int = 0
    error: str | None = None  # non-None if we fell back to the original text


class TextCorrector:
    """Corrects and improves transcribed text using an LLM.

    Prompts are loaded from prompts/*.yaml via the prompts registry. The caller
    picks mode ("transcription" or "prompt") and language; the registry resolves
    to the highest versioned prompt for that (mode, language) pair.
    """

    MODE_TRANSCRIPTION = "transcription"
    MODE_PROMPT = "prompt"

    def __init__(
        self,
        api_key: str,
        provider: str = "groq",
        model: str | None = None,
        mode: str = "prompt",
        language: str = "en",
    ):
        self._api_key = api_key
        self._provider = provider.lower()
        self._mode = mode
        self._language = language
        self._model = model or self._default_model()
        self._client = None
        self._enabled = True

    def _default_model(self) -> str:
        if self._provider == "openai":
            return "gpt-4o-mini"
        return "llama-3.3-70b-versatile"

    def _resolve_prompt(self) -> prompts.Prompt:
        return prompts.get(self._mode, self._language)

    def _get_client(self):
        """Lazily initialize the client based on provider."""
        if self._client is None:
            if self._provider == "openai":
                try:
                    from openai import OpenAI

                    self._client = OpenAI(api_key=self._api_key)
                except ImportError as err:
                    raise ImportError(
                        "openai package not installed. Run: pip install openai"
                    ) from err
            else:
                try:
                    from groq import Groq

                    self._client = Groq(api_key=self._api_key)
                except ImportError as err:
                    raise ImportError("groq package not installed. Run: pip install groq") from err
        return self._client

    def correct(self, text: str) -> CorrectionResult:
        """Correct the transcribed text.

        Always returns a CorrectionResult. On any failure (disabled, no key, too
        short, sanity-check rejection, API error) the `text` field holds the
        original input and `error` explains why.
        """
        started = time.perf_counter()

        def _passthrough(reason: str) -> CorrectionResult:
            return CorrectionResult(
                text=text,
                corrected=False,
                latency_ms=(time.perf_counter() - started) * 1000,
                error=reason,
                provider=self._provider,
                model=self._model,
            )

        if not self._enabled:
            return _passthrough("disabled")
        if not text:
            return _passthrough("empty input")
        if not self._api_key:
            return _passthrough("no API key")
        if len(text.split()) < 3:
            return _passthrough("too short")

        try:
            prompt = self._resolve_prompt()
        except KeyError as e:
            return _passthrough(f"prompt not found: {e}")

        try:
            client = self._get_client()
            response = client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": prompt.prompt},
                    {"role": "user", "content": text},
                ],
                temperature=0,
                max_tokens=1024,
            )

            corrected_text = response.choices[0].message.content.strip()

            # Sanity check: reject wildly different lengths (hallucination/truncation guard).
            if len(corrected_text) > len(text) * 2 or len(corrected_text) < len(text) * 0.3:
                return _passthrough("length sanity check failed")

            usage = getattr(response, "usage", None)
            prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
            completion_tokens = getattr(usage, "completion_tokens", 0) or 0
            total_tokens = getattr(usage, "total_tokens", prompt_tokens + completion_tokens) or 0

            return CorrectionResult(
                text=corrected_text,
                corrected=corrected_text != text,
                latency_ms=(time.perf_counter() - started) * 1000,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                model=self._model,
                provider=self._provider,
                prompt_id=prompt.id,
                prompt_version=prompt.version,
            )

        except Exception as e:
            print(f"Correction failed ({self._provider}): {e}")
            return _passthrough(f"api error: {e}")

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled

    def set_api_key(self, api_key: str) -> None:
        self._api_key = api_key
        self._client = None

    def set_provider(self, provider: str, api_key: str | None = None) -> None:
        self._provider = provider.lower()
        if api_key:
            self._api_key = api_key
        self._client = None
        self._model = self._default_model()

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def provider(self) -> str:
        return self._provider

    @property
    def mode(self) -> str:
        return self._mode

    def set_mode(self, mode: str) -> None:
        if mode in (self.MODE_TRANSCRIPTION, self.MODE_PROMPT):
            self._mode = mode

    def set_language(self, language: str) -> None:
        self._language = language

    def toggle_mode(self) -> str:
        self._mode = (
            self.MODE_PROMPT if self._mode == self.MODE_TRANSCRIPTION else self.MODE_TRANSCRIPTION
        )
        return self._mode
