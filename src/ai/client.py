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
# Gemini Stub
# ---------------------------------------------------------------------


class GeminiClient(BaseLLMClient):
    """
    Placeholder for future Gemini integration.
    """

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
    ) -> str:
        raise NotImplementedError(
            "Gemini client has not been implemented."
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
        ollama (default)

    OLLAMA_MODEL
        qwen2.5:7b (default)
    """

    provider = os.getenv(
        "LLM_PROVIDER",
        "ollama",
    ).lower()

    if provider == "ollama":
        return OllamaClient(
            model=os.getenv(
                "OLLAMA_MODEL",
                "qwen2.5:7b",
            )
        )

    if provider == "gemini":
        return GeminiClient()

    raise ValueError(
        f"Unsupported LLM provider: {provider}"
    )