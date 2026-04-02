"""Agent state definitions.

LangGraph nodes receive this state as a dict and return partial updates.
The framework merges updates into the state automatically.
Use Annotated types with reducers (e.g. operator.add) for fields that
should accumulate values across nodes instead of being replaced.
"""

import operator
from typing import Annotated, Optional
from typing_extensions import TypedDict


class AgentState(TypedDict, total=False):
    """State for the alpha_digest agent."""

    # Comma-separated ticker symbols provided by the user (e.g. "AAPL,MSFT,TSLA")
    query: str

    # Parsed list of ticker symbols
    tickers: list[str]

    # Fetched news articles — uses add reducer so multiple fetches accumulate
    data: Annotated[list[dict], operator.add]

    # Formatted text representation for LLM processing
    raw_text: Optional[str]

    # Generated summary or output from LLM processing
    summary: Optional[str]

    # Error message if any step fails
    error: Optional[str]
