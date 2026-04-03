"""Data source tools — Finnhub company-news integration."""

import time
from datetime import datetime, timedelta, timezone

import requests
import difflib

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

# ── Preprocessing configuration (configurable via environment) ────────
import os
MIN_SUMMARY_LEN = int(os.getenv("ALPHA_DIGEST_MIN_SUMMARY_LEN", "20"))
MIN_HEADLINE_LEN = int(os.getenv("ALPHA_DIGEST_MIN_HEADLINE_LEN", "15"))
SIMILARITY_THRESHOLD = float(os.getenv("ALPHA_DIGEST_SIMILARITY_THRESHOLD", "0.85"))


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


# ── Article preprocessing helpers ────────────────────────────────────────
def _is_small_article(
    article: dict,
    min_summary_len: int | None = None,
    min_headline_len: int | None = None,
) -> bool:
    """Return True if article is too small/noisy to include for LLM.
    
    Uses environment-configured defaults if parameters not provided.
    """
    summary_thresh = min_summary_len if min_summary_len is not None else MIN_SUMMARY_LEN
    headline_thresh = min_headline_len if min_headline_len is not None else MIN_HEADLINE_LEN
    
    headline = (article.get("headline") or "").strip()
    summary = (article.get("summary") or "").strip()
    if not headline and not summary:
        return True
    if len(headline) < headline_thresh and len(summary) < summary_thresh:
        return True
    return False


def _are_similar(text_a: str, text_b: str, threshold: float | None = None) -> bool:
    """Return True if two texts are similar above the threshold ratio.
    
    Uses environment-configured default if threshold not provided.
    Early exit if texts are too different in length (optimization).
    """
    if not text_a or not text_b:
        return False
    
    thresh = threshold if threshold is not None else SIMILARITY_THRESHOLD
    
    # Early exit: if lengths differ significantly, likely not similar
    len_ratio = min(len(text_a), len(text_b)) / max(len(text_a), len(text_b))
    if len_ratio < 0.6:  # less than 60% length match
        return False
    
    ratio = difflib.SequenceMatcher(None, text_a, text_b).ratio()
    return ratio >= thresh


def preprocess_articles(
    articles: list[dict],
    min_summary_len: int | None = None,
    min_headline_len: int | None = None,
    similarity_threshold: float | None = None,
) -> list[dict]:
    """Filter out small/noisy articles and collapse near-duplicates.

    - Removes articles with very short headlines and summaries.
    - Removes exact duplicates by URL.
    - Collapses similar articles (headline/summary) keeping the one
      with the longer summary (or the first seen if equal).
    
    Uses environment-configured defaults for thresholds if not provided.
    Returns detailed logs with counts of removed articles.
    """
    if not articles:
        return []

    initial_count = len(articles)
    seen_urls: set[str] = set()
    kept: list[dict] = []
    removed_small = 0
    removed_duplicates = 0
    collapsed_similar = 0

    for art in articles:
        # skip small/noisy articles
        if _is_small_article(art, min_summary_len, min_headline_len):
            removed_small += 1
            continue

        url = (art.get("url") or "").strip()
        if url and url in seen_urls:
            removed_duplicates += 1
            continue

        headline = (art.get("headline") or "").strip()
        summary = (art.get("summary") or "").strip()

        replaced = False
        for i, existing in enumerate(kept):
            ex_head = (existing.get("headline") or "").strip()
            ex_sum = (existing.get("summary") or "").strip()
            # if either headline or summary are similar, treat as duplicate
            if _are_similar(headline, ex_head, similarity_threshold) or _are_similar(summary, ex_sum, similarity_threshold):
                # prefer the article with longer summary (more content)
                if len(summary) > len(ex_sum):
                    kept[i] = art
                    if url:
                        seen_urls.add(url)
                collapsed_similar += 1
                replaced = True
                break

        if not replaced:
            kept.append(art)
            if url:
                seen_urls.add(url)

    logger.debug(
        "Preprocessing: %d initial | -%d small | -%d dupes | -%d similar → %d final",
        initial_count,
        removed_small,
        removed_duplicates,
        collapsed_similar,
        len(kept),
    )
    return kept


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

    # Preprocess combined articles to remove noise/duplicates before returning
    all_articles = preprocess_articles(all_articles)
    return all_articles


# ── Legacy wrappers (kept for backward compatibility) ────────────────────

def fetch_data(query: str = "", limit: int = 20, lookback_days: int = 1) -> list[dict]:
    """Parse *query* as comma-separated tickers and fetch Finnhub news.
    
    Args:
        query: Comma-separated ticker symbols (e.g. "AAPL,MSFT").
        limit: Max articles per ticker (default 20).
        lookback_days: How many days back to fetch (default 1).
        
    Returns:
        Preprocessed list of article dicts, deduplicated and noise-filtered.
    """
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
    return fetch_news_for_tickers(symbols, limit_per_ticker=limit, lookback_days=lookback_days)


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
