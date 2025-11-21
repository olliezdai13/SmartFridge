"""Utilities for normalizing product names returned by the vision model."""

from __future__ import annotations

import re
from typing import cast

import inflect
from inflect import Word

_NON_ALNUM_SPACE = re.compile(r"[^a-z0-9 ]+")
_COLLAPSE_SPACES = re.compile(r"\s+")
_INFLECT_ENGINE = inflect.engine()


def normalize_product_name(raw_name: str) -> str:
    """Normalize noisy fridge snapshot product names into a canonical form."""

    normalized = raw_name.lower().strip()
    if not normalized:
        return normalized

    normalized = normalized.replace("_", " ").replace("-", " ")
    normalized = _NON_ALNUM_SPACE.sub("", normalized)
    normalized = _COLLAPSE_SPACES.sub(" ", normalized).strip()

    if not normalized:
        return normalized

    parts = normalized.split(" ")
    last_word = cast(Word, parts[-1])
    singular = str(_INFLECT_ENGINE.singular_noun(last_word) or last_word)
    parts[-1] = singular

    return " ".join(parts)
