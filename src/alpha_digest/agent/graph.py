"""LangGraph agent workflow for alpha_digest.

Nodes receive the full state dict and return **partial updates** (only the
keys that changed).  LangGraph merges them back automatically.
"""

import asyncio
import os
from typing import Any, Dict, Optional

from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, StateGraph

from src.alpha_digest.config import (
    CHUNK_SIZE,
    DEFAULT_LOOKBACK_DAYS,
    DEFAULT_NEWS_PER_TICKER,
    DEFAULT_TICKERS,
    logger,
)
from src.alpha_digest.prompts import get_summary_prompt, get_chunk_merge_prompt
from src.alpha_digest.states import AgentState
from src.alpha_digest.tools import fetch_news_for_tickers, format_data_for_llm
from src.alpha_digest.utils import (
    get_api_key,
    generate_summary_audio,
    send_summary_email_oauth,
    send_summary_to_telegram,
)

# ── Constants ──────────────────────────────────────────────────────────
SEPARATOR_THRESHOLD = 10

# Response keys
RESP_DATA = "data"
RESP_RAW_TEXT = "raw_text"
RESP_SUMMARY = "summary"
RESP_ERROR = "error"
RESP_AUDIO_PATH = "audio_path"
RESP_EMAIL_STATUS = "email_status"
RESP_TELEGRAM_STATUS = "telegram_status"


# ── Helper: LLM singleton ───────────────────────────────────────────────
_llm_instance: ChatGoogleGenerativeAI | None = None


def _get_llm() -> ChatGoogleGenerativeAI:
    """Return a cached LLM instance."""
    global _llm_instance
    if _llm_instance is None:
        api_key = get_api_key()
        _llm_instance = ChatGoogleGenerativeAI(
            model="models/gemini-2.5-flash",
            temperature=0.7,
            google_api_key=api_key,
        )
    return _llm_instance


# ── Graph nodes ──────────────────────────────────────────────────────────

def parse_tickers_node(state: AgentState) -> dict:
    """Parse query into a list of ticker symbols."""
    query = state.get("query", "")
    tickers = [t.strip().upper() for t in query.split(",") if t.strip()]
    if not tickers:
        # Fall back to DEFAULT_TICKERS from config. If still empty, return an
        # error as before.
        if DEFAULT_TICKERS:
            logger.info(
                "parse_tickers_node: no query provided, falling back to DEFAULT_TICKERS: %s",
                DEFAULT_TICKERS,
            )
            tickers = list(DEFAULT_TICKERS)
        else:
            return {"error": "No ticker symbols provided. Pass e.g. 'AAPL,MSFT,TSLA'."}
    logger.info("parse_tickers_node: parsed tickers = %s", tickers)
    return {"tickers": tickers}


def fetch_data_node(state: AgentState) -> dict:
    """Fetch Finnhub company news for each ticker."""
    try:
        tickers = state.get("tickers", [])
        limit = int(os.getenv("NEWS_PER_TICKER", str(DEFAULT_NEWS_PER_TICKER)))
        lookback = int(os.getenv("LOOKBACK_DAYS", str(DEFAULT_LOOKBACK_DAYS)))

        data = fetch_news_for_tickers(
            symbols=tickers,
            limit_per_ticker=limit,
            lookback_days=lookback,
        )
        logger.info("fetch_data_node: %d total articles loaded", len(data))
        return {"data": data}

    except Exception as e:
        logger.error("fetch_data_node failed: %s", e)
        return {"error": f"Failed to fetch data: {e}"}


def format_data_node(state: AgentState) -> dict:
    """Format news articles for LLM processing."""
    try:
        data = state.get("data", [])
        raw_text = format_data_for_llm(data)

        # Log which tickers actually have articles going to the LLM
        from collections import Counter
        sym_counts = Counter(art.get("symbol", "?") for art in data)
        tickers_with_data = [sym for sym, _ in sym_counts.most_common()]
        logger.info(
            "format_data_node: %d chars, %d articles across %d tickers: %s",
            len(raw_text),
            len(data),
            len(tickers_with_data),
            ", ".join(f"{s}({c})" for s, c in sym_counts.most_common()),
        )

        # Narrow allowed_tickers to only those with actual data
        return {"raw_text": raw_text, "tickers_with_data": tickers_with_data}
    except Exception as e:
        logger.error("format_data_node failed: %s", e)
        return {"error": f"Failed to format data: {e}"}


async def process_node(state: AgentState) -> dict:
    """Summarize the news with LLM, with parallel chunking for very large inputs."""
    try:
        raw_text = state.get("raw_text")
        tickers = state.get("tickers", [])
        tickers_with_data = state.get("tickers_with_data", tickers)
        if not raw_text:
            return {"error": "No content to process"}
        if not tickers_with_data:
            return {"error": "No ticker symbols with data available for summarization"}

        llm = _get_llm()
        logger.info(
            "process_node: summarizing %d tickers with data: %s",
            len(tickers_with_data),
            ", ".join(tickers_with_data),
        )

        # ── Split into article blocks ────────────────────────────────
        lines = raw_text.split("\n")
        blocks: list[str] = []
        current: list[str] = []
        for line in lines:
            current.append(line)
            if line.startswith("-" * SEPARATOR_THRESHOLD):
                blocks.append("\n".join(current))
                current = []
        if current:
            blocks.append("\n".join(current))

        if len(blocks) <= CHUNK_SIZE:
            # Single call – fits within context window
            prompt = get_summary_prompt(raw_text, allowed_tickers=tickers_with_data)
            response = await llm.ainvoke([HumanMessage(content=prompt)])
            summary = response.content
        else:
            # Parallel chunk calls → single merge call
            num_chunks = (len(blocks) + CHUNK_SIZE - 1) // CHUNK_SIZE
            logger.info(
                "Very large input (%d blocks) – %d parallel chunks of %d",
                len(blocks),
                num_chunks,
                CHUNK_SIZE,
            )
            chunk_prompts = [
                get_summary_prompt(
                    "\n".join(blocks[start : start + CHUNK_SIZE]),
                    allowed_tickers=tickers_with_data,
                )
                for start in range(0, len(blocks), CHUNK_SIZE)
            ]
            chunk_responses = await asyncio.gather(
                *[llm.ainvoke([HumanMessage(content=p)]) for p in chunk_prompts]
            )
            partial_summaries = [r.content for r in chunk_responses]

            merge_prompt = get_chunk_merge_prompt(
                partial_summaries,
                allowed_tickers=tickers_with_data,
            )
            merged = await llm.ainvoke([HumanMessage(content=merge_prompt)])
            summary = merged.content

        logger.info("process_node: summary generated (%d chars)", len(summary))
        return {"summary": summary, "raw_text": None}

    except Exception as e:
        logger.error("process_node failed: %s", e)
        return {"error": f"Failed to process data: {e}"}


def error_handler_node(state: AgentState) -> dict:
    """Log the error and pass state through."""
    logger.error("Pipeline error: %s", state.get("error"))
    return {}


def should_fetch(state: AgentState) -> str:
    """Determine if we have valid tickers to fetch."""
    if state.get("error"):
        return "error_handler"
    return "fetch_data"


def should_process(state: AgentState) -> str:
    """Determine if processing should proceed."""
    if state.get("error") or not state.get("data"):
        return "error_handler"
    return "format_data"


# ── Graph construction ───────────────────────────────────────────────────

def create_agent_graph():
    """Create and compile the LangGraph workflow."""
    graph = StateGraph(AgentState)

    graph.add_node("parse_tickers", parse_tickers_node)
    graph.add_node("fetch_data", fetch_data_node)
    graph.add_node("format_data", format_data_node)
    graph.add_node("process", process_node)
    graph.add_node("error_handler", error_handler_node)

    graph.set_entry_point("parse_tickers")
    graph.add_conditional_edges("parse_tickers", should_fetch)
    graph.add_conditional_edges("fetch_data", should_process)
    graph.add_edge("format_data", "process")
    graph.add_edge("process", END)
    graph.add_edge("error_handler", END)

    return graph.compile()


# ── Async runner with parallel TTS + email + Telegram ────────────────────

async def run_agent(
    query: Optional[str] = None,
) -> dict:
    """Run the agent pipeline asynchronously.

    Args:
        query: Comma-separated ticker symbols (e.g. "AAPL,MSFT,TSLA")

    Returns:
        Dictionary with data, raw text, summary, error, and delivery statuses
    """
    agent = create_agent_graph()

    initial_state: AgentState = {"query": query or ""}

    result = await agent.ainvoke(initial_state)
    logger.info("Agent graph execution completed")

    response: Dict[str, Any] = {
        RESP_DATA: result.get("data"),
        RESP_RAW_TEXT: result.get("raw_text"),
        RESP_SUMMARY: result.get("summary"),
        RESP_ERROR: result.get("error"),
    }

    tickers_str = ",".join(result.get("tickers", []))

    if response.get(RESP_SUMMARY) and not response.get(RESP_ERROR):
        # ── Generate TTS audio first ────────────────────────────────
        audio_path = await _safe_tts(response[RESP_SUMMARY])
        response[RESP_AUDIO_PATH] = audio_path

        # ── Send email (text only) and Telegram (with MP3) in parallel ─────
        email_task = asyncio.create_task(_safe_email(
            response[RESP_SUMMARY], tickers_str, None  # No audio attachment
        ))
        telegram_task = asyncio.create_task(_safe_telegram(
            audio_path,  # MP3 only to Telegram
        ))

        response[RESP_EMAIL_STATUS] = await email_task
        response[RESP_TELEGRAM_STATUS] = await telegram_task

        email_ok = response[RESP_EMAIL_STATUS] == "sent"
        telegram_ok = response[RESP_TELEGRAM_STATUS] == "sent"

        if email_ok and telegram_ok:
            logger.info("Email and Telegram notifications sent")
        else:
            if not email_ok:
                logger.warning("Email status: %s", response[RESP_EMAIL_STATUS])
            if not telegram_ok:
                logger.warning("Telegram status: %s", response[RESP_TELEGRAM_STATUS])

    return response


async def _safe_tts(summary: str) -> Optional[str]:
    """Generate TTS audio, returning None on failure."""
    try:
        return await generate_summary_audio(summary)
    except Exception as e:
        logger.error("TTS generation failed: %s", e)
        return None


async def _safe_email(summary: str, tickers: str, audio_path: Optional[str]) -> str:
    """Send email summary, returning status string instead of raising."""
    try:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, send_summary_email_oauth, summary, tickers, audio_path,
        )
    except Exception as e:
        logger.error("Email send failed: %s", e)
        return f"failed: {e}"


async def _safe_telegram(audio_path: Optional[str]) -> str:
    """Send TTS audio to Telegram, returning status string instead of raising."""
    try:
        return await send_summary_to_telegram(audio_path)
    except Exception as e:
        logger.error("Telegram send failed: %s", e)
        return f"failed: {e}"
