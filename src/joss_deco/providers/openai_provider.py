from __future__ import annotations

from openai import OpenAI

from .base import LLMProvider


class OpenAIProvider(LLMProvider):
    def __init__(self) -> None:
        self._client = OpenAI()

    def generate(self, *, model: str, messages: list[dict], temperature: float, max_tokens: int) -> str:
        try:
            response = self._client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            text = response.choices[0].message.content
        except Exception as exc:
            raise RuntimeError(f"OpenAI request failed for model '{model}': {exc}") from exc

        if not text:
            raise RuntimeError(f"OpenAI returned an empty response for model '{model}'.")
        return text.strip()
