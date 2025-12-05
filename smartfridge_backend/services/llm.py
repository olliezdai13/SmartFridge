"""Client helpers for interacting with a vision-capable LLM."""

from __future__ import annotations

import base64
import json
import logging
from dataclasses import dataclass
from json import JSONDecodeError
from typing import Any, Optional

from httpx import RequestError, TimeoutException
from openai import OpenAI
from openai.types.responses import Response

logger = logging.getLogger(__name__)


@dataclass
class VisionLLMSettings:
    """Configuration required to talk to the vision model."""

    api_key: str
    model: str = "gpt-5-mini"
    system_prompt: Optional[str] = None


@dataclass(slots=True)
class VisionLLMResult:
    """Container for the raw and parsed outputs from the vision model."""

    raw_text: str
    parsed_json: Any | None


@dataclass
class TextLLMSettings:
    """Configuration required to talk to a text-only model."""

    api_key: str
    model: str = "gpt-5-mini"
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
    ) -> VisionLLMResult:
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

        try:
            response: Response = self._client.responses.create(
                model=self._settings.model,
                input=content,
            )
        except TimeoutException as e:
            logger.error("OpenAI / HTTP timeout: %r", e)
            raise
        except RequestError as e:
            logger.error("OpenAI / HTTP network error: %r", e)
            raise
        except Exception:
            logger.exception("OpenAI response error")
            raise

        output_text = response.output_text
        return VisionLLMResult(
            raw_text=output_text,
            parsed_json=self._attempt_json_parse(output_text),
        )

    @staticmethod
    def _attempt_json_parse(text: str) -> Any | None:
        """Try to convert the LLM's text output into JSON."""
        candidate = (text or "").strip()
        if not candidate:
            return None

        start = candidate.find("{")
        end = candidate.rfind("}")
        if start == -1 or end == -1 or end < start:
            return None
        candidate = candidate[start : end + 1]

        try:
            return json.loads(candidate)
        except JSONDecodeError:
            logger.debug("LLM output was not valid JSON", exc_info=True)
            return None


class TextLLMClient:
    """Minimal client for JSON-friendly text prompts."""

    def __init__(self, settings: TextLLMSettings) -> None:
        self._settings = settings
        self._client = OpenAI(api_key=settings.api_key)

    def run_prompt(
        self, *, prompt: str, system_prompt: str | None = None
    ) -> VisionLLMResult:
        """Send a text-only prompt to the configured LLM."""

        user_text = (prompt or "").strip()
        if not user_text:
            raise ValueError("prompt is required")

        merged_system_prompt = (system_prompt or self._settings.system_prompt) or ""
        content = []
        if merged_system_prompt:
            content.append(
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": merged_system_prompt,
                        }
                    ],
                }
            )

        content.append(
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": user_text},
                ],
            }
        )

        try:
            response: Response = self._client.responses.create(
                model=self._settings.model,
                input=content,
            )
        except TimeoutException as e:
            logger.error("OpenAI / HTTP timeout: %r", e)
            raise
        except RequestError as e:
            logger.error("OpenAI / HTTP network error: %r", e)
            raise
        except Exception:
            logger.exception("OpenAI response error")
            raise

        output_text = response.output_text
        return VisionLLMResult(
            raw_text=output_text,
            parsed_json=VisionLLMClient._attempt_json_parse(output_text),
        )


def init_vision_llm_client(settings: VisionLLMSettings) -> VisionLLMClient:
    """Create a ``VisionLLMClient`` instance from the provided settings."""

    return VisionLLMClient(settings)


def init_text_llm_client(settings: TextLLMSettings) -> TextLLMClient:
    """Create a ``TextLLMClient`` instance from the provided settings."""

    return TextLLMClient(settings)
