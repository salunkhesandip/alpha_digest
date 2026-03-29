"""Credential utilities for the agent."""

import os


def get_api_key() -> str:
    """Get the LLM API key from environment.

    Returns:
        API key string

    Raises:
        ValueError: If API key is not set
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("Please set GOOGLE_API_KEY environment variable")
    return api_key
