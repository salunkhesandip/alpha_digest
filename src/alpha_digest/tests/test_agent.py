"""Tests for the alpha_digest agent."""

import pytest
from alpha_digest.states import AgentState
from alpha_digest.tools import format_data_for_llm


@pytest.fixture
def sample_data():
    """Sample data items for testing."""
    return [
        {
            "id": "1",
            "title": "First Item",
            "text": "This is the content of the first item for testing.",
            "score": 42,
        },
        {
            "id": "2",
            "title": "Second Item",
            "text": "This is the content of the second item for testing.",
            "score": 120,
        },
    ]


def test_format_data_for_llm(sample_data):
    """Test formatting data for LLM."""
    formatted = format_data_for_llm(sample_data)

    assert "Stock Market News" in formatted
    assert "Ticker: UNKNOWN" in formatted
    assert formatted.count("Headline: No headline") == 2
    assert formatted.count("Source:   Unknown source") == 2


def test_format_empty_data():
    """Test formatting empty data list."""
    formatted = format_data_for_llm([])
    assert "No news articles found for the requested tickers." in formatted


def test_agent_state():
    """Test AgentState initialization."""
    state: AgentState = {"query": "test query"}

    assert state["query"] == "test query"
    assert "summary" not in state
    assert "error" not in state


def test_agent_state_with_data(sample_data):
    """Test AgentState with data."""
    state: AgentState = {"data": sample_data}

    assert len(state["data"]) == 2
    assert state["data"][0]["id"] == "1"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
