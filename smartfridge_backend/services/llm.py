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

    def analyze_image(self, *, prompt: str, image_bytes: bytes) -> str:
        """Send the given prompt and image to the configured LLM."""
        if not prompt:
            raise ValueError("prompt is required")
        if not image_bytes:
            raise ValueError("image_bytes is empty")

        image_base64 = base64.b64encode(image_bytes).decode("ascii")

        content = []
        if self._settings.system_prompt:
            content.append(
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "text",
                            "text": self._settings.system_prompt,
                        }
                    ],
                }
            )

        content.append(
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {"type": "input_image", "image_base64": image_base64},
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
