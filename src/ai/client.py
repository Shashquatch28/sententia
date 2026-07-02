"""
src/ai/client.py

LLM provider abstraction for HireIQ.

Responsibilities
----------------
- Provide a common interface for all LLM providers.
- Handle provider configuration.
- Execute prompts.
- Surface provider errors cleanly.

No retrieval.
No recruiter logic.
No prompt definitions.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod

import requests


GEMINI_MODEL_ALIASES = {
    "gemini-1.5-flash": "gemini-2.5-flash-lite",
}


# ---------------------------------------------------------------------
# Base Client
# ---------------------------------------------------------------------


class BaseLLMClient(ABC):
    """Abstract interface for all LLM providers."""

    @abstractmethod
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
    ) -> str:
        raise NotImplementedError


# ---------------------------------------------------------------------
# Ollama Client
# ---------------------------------------------------------------------


class OllamaClient(BaseLLMClient):
    """
    Local Ollama client.
    """

    def __init__(
        self,
        model: str = "qwen2.5:7b",
        host: str = "http://localhost:11434",
    ) -> None:
        self.model = model
        self.host = host.rstrip("/")

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
    ) -> str:

        payload = {
            "model": self.model,
            "system": system_prompt,
            "prompt": user_prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
            },
        }

        try:
            response = requests.post(
                f"{self.host}/api/generate",
                json=payload,
                timeout=120,
            )

            response.raise_for_status()

            data = response.json()

            return data.get("response", "").strip()

        except requests.exceptions.ConnectionError:
            raise RuntimeError(
                "Unable to connect to Ollama. Is Ollama running?"
            )

        except requests.exceptions.Timeout:
            raise RuntimeError(
                "Ollama request timed out."
            )

        except Exception as e:
            raise RuntimeError(
                f"Ollama error: {e}"
            )


# ---------------------------------------------------------------------
# Hosted Clients
# ---------------------------------------------------------------------


class GeminiClient(BaseLLMClient):
    """
    Google Gemini API client.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.5-flash-lite",
    ) -> None:
        self.api_key = api_key
        self.model = GEMINI_MODEL_ALIASES.get(model, model)

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
    ) -> str:
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY or LLM_API_KEY is required.")

        payload = {
            "systemInstruction": {
                "parts": [{"text": system_prompt}],
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user_prompt}],
                }
            ],
            "generationConfig": {
                "temperature": temperature,
            },
        }

        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent"
        )

        try:
            response = requests.post(
                url,
                params={"key": self.api_key},
                json=payload,
                timeout=120,
            )
            response.raise_for_status()
            data = response.json()
            candidates = data.get("candidates") or []
            parts = (
                candidates[0]
                .get("content", {})
                .get("parts", [])
                if candidates
                else []
            )
            text = "".join(part.get("text", "") for part in parts).strip()
            if not text:
                raise RuntimeError("Gemini returned an empty response.")
            return text
        except requests.exceptions.Timeout:
            raise RuntimeError("Gemini request timed out.")
        except requests.exceptions.HTTPError as e:
            raise RuntimeError(f"Gemini API error: {e.response.text[:500]}")
        except Exception as e:
            raise RuntimeError(f"Gemini error: {e}")


class OpenAICompatibleClient(BaseLLMClient):
    """
    Chat-completions client for OpenAI, Groq, OpenRouter, and compatible APIs.
    """

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
    ) -> str:
        if not self.api_key:
            raise RuntimeError("LLM_API_KEY is required.")
        if not self.model:
            raise RuntimeError("LLM_MODEL is required.")
        if not self.base_url:
            raise RuntimeError("LLM_API_BASE is required.")

        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
        }

        try:
            response = requests.post(
                url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=120,
            )
            response.raise_for_status()
            data = response.json()
            text = (
                data.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
                .strip()
            )
            if not text:
                raise RuntimeError("LLM returned an empty response.")
            return text
        except requests.exceptions.Timeout:
            raise RuntimeError("LLM request timed out.")
        except requests.exceptions.HTTPError as e:
            raise RuntimeError(
                f"OpenAI-compatible API error: {e.response.text[:500]}"
            )
        except Exception as e:
            raise RuntimeError(f"OpenAI-compatible LLM error: {e}")


class DisabledLLMClient(BaseLLMClient):
    """
    Explicit fallback when no hosted or local LLM provider is configured.
    """

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
    ) -> str:
        raise RuntimeError(
            "No LLM provider configured. Set LLM_PROVIDER and the provider API key."
        )


# ---------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------


def get_client() -> BaseLLMClient:
    """
    Return the configured LLM provider.

    Environment Variables
    ---------------------
    LLM_PROVIDER
        ollama, gemini, openai, openai_compatible, groq, disabled

    OLLAMA_MODEL
        qwen2.5:7b (default)
    """

    provider = os.getenv(
        "LLM_PROVIDER",
        "disabled",
    ).lower()

    if provider == "ollama":
        return OllamaClient(
            model=os.getenv(
                "OLLAMA_MODEL",
                "qwen2.5:7b",
            )
        )

    if provider == "gemini":
        return GeminiClient(
            api_key=os.getenv("GEMINI_API_KEY", os.getenv("LLM_API_KEY", "")),
            model=os.getenv("LLM_MODEL", "gemini-2.5-flash-lite"),
        )

    if provider == "openai":
        return OpenAICompatibleClient(
            api_key=os.getenv("OPENAI_API_KEY", os.getenv("LLM_API_KEY", "")),
            model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
            base_url=os.getenv("LLM_API_BASE", "https://api.openai.com/v1"),
        )

    if provider == "groq":
        return OpenAICompatibleClient(
            api_key=os.getenv("GROQ_API_KEY", os.getenv("LLM_API_KEY", "")),
            model=os.getenv("LLM_MODEL", "llama-3.1-8b-instant"),
            base_url=os.getenv("LLM_API_BASE", "https://api.groq.com/openai/v1"),
        )

    if provider in ("openai_compatible", "compatible"):
        return OpenAICompatibleClient(
            api_key=os.getenv("LLM_API_KEY", ""),
            model=os.getenv("LLM_MODEL", ""),
            base_url=os.getenv("LLM_API_BASE", ""),
        )

    if provider == "disabled":
        return DisabledLLMClient()

    raise ValueError(
        f"Unsupported LLM provider: {provider}"
    )
