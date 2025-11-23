"""Defaults for the vision LLM that are tracked in Git."""

# Model version used by default. Can be overridden via env if needed.
DEFAULT_LLM_MODEL = "gpt-4o-mini"

# Canonical system prompt for vision analysis requests.
DEFAULT_LLM_SYSTEM_PROMPT = (
    'List all ingredients in this fridge in JSON format {"ingredient":#,...}. '
    'Example output: {"lime":5, "milk":1, "chicken":1, "soda":4}. '
    'Use generic names for branded items, like "kombucha" rather than "health_ade_kombucha". '
    'Focus on the core ingredient, and avoid any adjectives or modifiers. Prefer "milk" over "whole_milk". '
    "Only output JSON format. NO ADDITIONAL TEXT!"
)
