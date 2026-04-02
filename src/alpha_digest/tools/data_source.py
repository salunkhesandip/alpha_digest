"""Data source tools — Finnhub company-news integration."""

import time
from datetime import datetime, timedelta, timezone

import requests

from src.alpha_digest.config import (
    API_TIMEOUT,
    CACHE_TTL,
    FINNHUB_BASE_URL,
    DEFAULT_TICKERS,
    MAX_RETRIES,
    RETRY_BACKOFF_BASE,
    logger,
)
from src.alpha_digest.utils import get_finnhub_api_key


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


# ── Finnhub company-news fetcher ─────────────────────────────────────────

def _fetch_company_news(
    symbol: str,
    from_date: str,
    to_date: str,
    token: str,
) -> list[dict]:
    """GET https://finnhub.io/api/v1/company-news for a single ticker."""
    url = f"{FINNHUB_BASE_URL}/company-news"
    params = {
        "symbol": symbol,
        "from": from_date,
        "to": to_date,
        "token": token,
    }
    resp = requests.get(url, params=params, timeout=API_TIMEOUT)
    resp.raise_for_status()
    return resp.json()  # list of article dicts


def fetch_news_for_tickers(
    symbols: list[str],
    limit_per_ticker: int = 20,
    lookback_days: int = 1,
) -> list[dict]:
    """Fetch Finnhub company news for every ticker in *symbols*.

    Args:
        symbols: List of ticker symbols (e.g. ["AAPL", "MSFT"]).
        limit_per_ticker: Max articles kept per ticker.
        lookback_days: How many days back to fetch (default 1 = last day).

    Returns:
        Combined list of article dicts, each tagged with ``symbol``.
    """
    token = get_finnhub_api_key()
    today = datetime.now(timezone.utc).date()
    from_date = (today - timedelta(days=lookback_days)).isoformat()
    to_date = today.isoformat()

    all_articles: list[dict] = []

    for sym in symbols:
        sym = sym.strip().upper()
        cache_key = _cache_key("finnhub", sym, limit_per_ticker)
        cached = _get_cached(cache_key)
        if cached is not None:
            all_articles.extend(cached)
            continue

        try:
            articles = _retry(
                _fetch_company_news, sym, from_date, to_date, token
            )
            # Keep only the most recent *limit_per_ticker* articles
            articles = articles[:limit_per_ticker]
            # Preserve Finnhub metadata and group by the queried ticker.
            for art in articles:
                if "symbol" in art:
                    art["_finnhub_symbol"] = art["symbol"]
                if "related" in art:
                    related = art["related"]
                    art["_finnhub_related"] = (
                        [item.upper() for item in related]
                        if isinstance(related, list)
                        else [part.strip().upper() for part in str(related).split(",") if part.strip()]
                    )
                art["symbol"] = sym
            _set_cache(cache_key, articles)
            logger.info("Fetched %d articles for %s", len(articles), sym)
            all_articles.extend(articles)
        except Exception as exc:
            logger.error("Failed to fetch news for %s: %s", sym, exc)

    return all_articles


# ── Legacy wrappers (kept for backward compatibility) ────────────────────

def fetch_data(query: str = "", limit: int = 20) -> list[dict]:
    """Parse *query* as comma-separated tickers and fetch Finnhub news."""
    symbols = [s.strip().upper() for s in query.split(",") if s.strip()]
    if not symbols:
        # Fall back to DEFAULT_TICKERS from config (can be set via
        # ALPHA_DIGEST_TICKERS environment variable). If still empty, raise.
        if DEFAULT_TICKERS:
            symbols = DEFAULT_TICKERS
        else:
            raise ValueError(
                "Provide at least one ticker symbol (e.g. 'AAPL,MSFT') "
                "or set ALPHA_DIGEST_TICKERS environment variable."
            )
    return fetch_news_for_tickers(symbols, limit_per_ticker=limit)


def format_data_for_llm(data: list[dict]) -> str:
    """Format Finnhub news articles into readable text for LLM."""
    if not data:
        return "No news articles found for the requested tickers."

    formatted = "=== Stock Market News ===\n\n"
    current_symbol = None

    for article in data:
        sym = article.get("symbol", "UNKNOWN")
        if sym != current_symbol:
            current_symbol = sym
            formatted += f"\n{'=' * 50}\n  Ticker: {sym}\n{'=' * 50}\n\n"

        headline = article.get("headline", "No headline")
        source = article.get("source", "Unknown source")
        summary = article.get("summary", "")
        url = article.get("url", "")
        ts = article.get("datetime")
        date_str = (
            datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            if ts
            else "Unknown date"
        )

        formatted += f"Headline: {headline}\n"
        formatted += f"Source:   {source}\n"
        formatted += f"Date:     {date_str}\n"
        if summary:
            formatted += f"Summary:  {summary}\n"
        if url:
            formatted += f"URL:      {url}\n"
        formatted += "-" * 50 + "\n\n"

    return formatted
