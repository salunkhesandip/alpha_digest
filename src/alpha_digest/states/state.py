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
    """State for the alpha_digest agent.

    Customize this state class to hold all the data your agent needs
    as it flows through the graph nodes.
    """

    # Input query or parameter for the agent
    query: str

    # Fetched data items — uses add reducer so multiple fetches accumulate
    data: Annotated[list[dict], operator.add]

    # Formatted text representation for LLM processing
    raw_text: Optional[str]

    # Generated summary or output from LLM processing
    summary: Optional[str]

    # Error message if any step fails
    error: Optional[str]
