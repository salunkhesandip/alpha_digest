"""LangGraph agent workflow for alpha_digest.

Nodes receive the full state dict and return **partial updates** (only the
keys that changed).  LangGraph merges them back automatically.
"""

import os
from typing import Any, Optional

from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, StateGraph

from src.alpha_digest.config import CHUNK_SIZE, logger
from src.alpha_digest.prompts import get_summary_prompt, get_chunk_merge_prompt
from src.alpha_digest.states import AgentState
from src.alpha_digest.tools import fetch_data, format_data_for_llm
from src.alpha_digest.utils import get_api_key

# ── Constants ──────────────────────────────────────────────────────────
DEFAULT_ITEM_LIMIT = 50
SEPARATOR_THRESHOLD = 10

# Response keys
RESP_DATA = "data"
RESP_RAW_TEXT = "raw_text"
RESP_SUMMARY = "summary"
RESP_ERROR = "error"


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
# Each node returns a **partial dict** — only the keys that changed.

def fetch_data_node(state: AgentState) -> dict:
    """Fetch data from external source.

    TODO: Implement your data fetching logic here.
    """
    try:
        try:
            limit = int(os.getenv("ITEM_LIMIT", str(DEFAULT_ITEM_LIMIT)))
        except ValueError:
            logger.warning("Invalid ITEM_LIMIT, using default %d", DEFAULT_ITEM_LIMIT)
            limit = DEFAULT_ITEM_LIMIT

        data = fetch_data(query=state["query"], limit=limit)
        logger.info("fetch_data_node: %d items loaded", len(data))
        return {"data": data}

    except Exception as e:
        logger.error("fetch_data_node failed: %s", e)
        return {"error": f"Failed to fetch data: {e}"}


def format_data_node(state: AgentState) -> dict:
    """Format data for LLM processing."""
    try:
        raw_text = format_data_for_llm(state.get("data", []))
        logger.info(
            "format_data_node: formatted text length = %d chars",
            len(raw_text),
        )
        return {"raw_text": raw_text}
    except Exception as e:
        logger.error("format_data_node failed: %s", e)
        return {"error": f"Failed to format data: {e}"}


def process_node(state: AgentState) -> dict:
    """Process data with LLM (summarize, analyze, etc.), with chunking for large inputs."""
    try:
        raw_text = state.get("raw_text")
        if not raw_text:
            return {"error": "No content to process"}

        llm = _get_llm()

        # ── Chunking: split long inputs into batches ─────────────────
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
            # Single-shot processing
            prompt = get_summary_prompt(raw_text)
            response = llm.invoke([HumanMessage(content=prompt)])
            summary = response.content
        else:
            # Chunk → process each → merge
            logger.info(
                "Large input (%d blocks) – chunking into batches of %d",
                len(blocks),
                CHUNK_SIZE,
            )
            partial_summaries: list[str] = []
            for start in range(0, len(blocks), CHUNK_SIZE):
                chunk_text = "\n".join(blocks[start : start + CHUNK_SIZE])
                prompt = get_summary_prompt(chunk_text)
                resp = llm.invoke([HumanMessage(content=prompt)])
                partial_summaries.append(resp.content)

            merge_prompt = get_chunk_merge_prompt(partial_summaries)
            merged = llm.invoke([HumanMessage(content=merge_prompt)])
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


def should_process(state: AgentState) -> str:
    """Determine if processing should proceed."""
    if state.get("error") or not state.get("data"):
        return "error_handler"
    return "format_data"


# ── Graph construction ───────────────────────────────────────────────────

def create_agent_graph():
    """Create and compile the LangGraph workflow."""
    graph = StateGraph(AgentState)

    graph.add_node("fetch_data", fetch_data_node)
    graph.add_node("format_data", format_data_node)
    graph.add_node("process", process_node)
    graph.add_node("error_handler", error_handler_node)

    graph.set_entry_point("fetch_data")
    graph.add_conditional_edges("fetch_data", should_process)
    graph.add_edge("format_data", "process")
    graph.add_edge("process", END)
    graph.add_edge("error_handler", END)

    return graph.compile()


# ── Async runner ─────────────────────────────────────────────────────────

async def run_agent(
    query: Optional[str] = None,
) -> dict:
    """Run the agent pipeline asynchronously.

    Args:
        query: Optional input query or parameter

    Returns:
        Dictionary with data, raw text, summary, and error
    """
    agent = create_agent_graph()

    initial_state: AgentState = {"query": query or ""}

    result = await agent.ainvoke(initial_state)
    logger.info("Agent graph execution completed")

    return {
        RESP_DATA: result.get("data"),
        RESP_RAW_TEXT: result.get("raw_text"),
        RESP_SUMMARY: result.get("summary"),
        RESP_ERROR: result.get("error"),
    }
