"""Client helpers for interacting with a vision-capable LLM."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Optional

from openai import OpenAI
from openai.types.responses import Response


@dataclass
class VisionLLMSettings:
    """Configuration required to talk to the vision model."""

    api_key: str
    model: str = "gpt-4o-mini"
    system_prompt: Optional[str] = None


class VisionLLMClient:
    """Thin wrapper around the OpenAI Responses API for vision requests."""

    def __init__(self, settings: VisionLLMSettings) -> None:
        self._settings = settings
        self._client = OpenAI(api_key=settings.api_key)

    def analyze_image(
        self,
        *,
        image_bytes: bytes,
        prompt: str | None = None,
        mime_type: str | None = None,
    ) -> str:
        """Send the given prompt and image to the configured LLM."""
        if not image_bytes:
            raise ValueError("image_bytes is empty")

        image_base64 = base64.b64encode(image_bytes).decode("ascii")

        user_text = (prompt or "").strip() or self._settings.system_prompt
        if not user_text:
            raise ValueError(
                "prompt is required when SMARTFRIDGE_LLM_SYSTEM_PROMPT is not set"
            )

        mime = (mime_type or "image/jpeg").strip() or "image/jpeg"
        data_uri = f"data:{mime};base64,{image_base64}"

        content = []
        if self._settings.system_prompt:
            content.append(
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": self._settings.system_prompt,
                        }
                    ],
                }
            )

        content.append(
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": user_text},
                    {"type": "input_image", "image_url": data_uri},
                ],
            }
        )

        response: Response = self._client.responses.create(
            model=self._settings.model,
            input=content,
        )

        return response.output_text


def init_vision_llm_client(settings: VisionLLMSettings) -> VisionLLMClient:
    """Create a ``VisionLLMClient`` instance from the provided settings."""

    return VisionLLMClient(settings)
