"""Data source tools for fetching and formatting data.

TODO: Replace this with your actual data source integration
(e.g., API client, database connector, web scraper, etc.)
"""

import time
from typing import Optional

from src.alpha_digest.config import (
    CACHE_TTL,
    MAX_RETRIES,
    RETRY_BACKOFF_BASE,
    logger,
)


# ── Simple in-memory cache ──────────────────────────────────────────────
_cache: dict[str, tuple[float, list[dict]]] = {}


def _cache_key(kind: str, query: str, limit: int) -> str:
    return f"{kind}:{query}:{limit}"


def _get_cached(key: str) -> list[dict] | None:
    entry = _cache.get(key)
    if entry and (time.time() - entry[0]) < CACHE_TTL:
        logger.info("Cache hit for %s", key)
        return entry[1]
    return None


def _set_cache(key: str, data: list[dict]) -> None:
    _cache[key] = (time.time(), data)


# ── Retry helper ─────────────────────────────────────────────────────────
def _retry(fn, *args, **kwargs):
    """Call *fn* with exponential back-off on failure."""
    last_exc: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            last_exc = exc
            wait = RETRY_BACKOFF_BASE ** attempt
            logger.warning(
                "Attempt %d/%d failed (%s). Retrying in %ds…",
                attempt,
                MAX_RETRIES,
                exc,
                wait,
            )
            time.sleep(wait)
    raise RuntimeError(
        f"All {MAX_RETRIES} attempts failed. Last error: {last_exc}"
    ) from last_exc


def fetch_data(query: str = "", limit: int = 20) -> list[dict]:
    """Fetch data from your external source.

    TODO: Replace this stub with your actual data fetching logic.

    Args:
        query: Search query or identifier
        limit: Maximum number of items to fetch

    Returns:
        List of data items as dictionaries
    """
    cache_key = _cache_key("default", query, limit)
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    def _fetch():
        # TODO: Replace with your actual API/data source call
        # Example structure:
        # response = your_api_client.get_data(query=query, limit=limit)
        # return [{"id": item.id, "text": item.text, ...} for item in response]
        raise NotImplementedError(
            "Replace this stub in tools/data_source.py with your actual data fetching logic."
        )

    try:
        data = _retry(_fetch)
        _set_cache(cache_key, data)
        return data
    except Exception as e:
        raise RuntimeError(f"Failed to fetch data: {e!s}")


def format_data_for_llm(data: list[dict]) -> str:
    """Format data items into readable text for LLM processing.

    TODO: Customize the formatting to match your data structure.

    Args:
        data: List of data items

    Returns:
        Formatted text representation
    """
    if not data:
        return "No data found."

    formatted = "=== Data Items ===\n\n"

    for i, item in enumerate(data, 1):
        formatted += f"Item {i}:\n"
        for key, value in item.items():
            formatted += f"  {key}: {value}\n"
        formatted += "-" * 50 + "\n\n"

    return formatted
