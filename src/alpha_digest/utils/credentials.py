"""Credential utilities for the agent."""

import os


def get_api_key() -> str:
    """Get the LLM API key from environment."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("Please set GOOGLE_API_KEY environment variable")
    return api_key


def get_finnhub_api_key() -> str:
    """Get the Finnhub API key from environment."""
    api_key = os.getenv("FINNHUB_API_KEY")
    if not api_key:
        raise ValueError("Please set FINNHUB_API_KEY environment variable")
    return api_key
