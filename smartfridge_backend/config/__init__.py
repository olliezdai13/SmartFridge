"""Static configuration shipped with the codebase."""

# LLM defaults are in a dedicated module for clarity and reuse.
from .llm import DEFAULT_LLM_MODEL, DEFAULT_LLM_SYSTEM_PROMPT

__all__ = ["DEFAULT_LLM_MODEL", "DEFAULT_LLM_SYSTEM_PROMPT"]
