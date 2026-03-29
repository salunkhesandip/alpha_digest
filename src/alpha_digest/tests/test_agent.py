"""Tests for the alpha_digest agent."""

import pytest
from src.alpha_digest.states import AgentState
from src.alpha_digest.tools import format_data_for_llm


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

    assert "Data Items" in formatted
    assert "First Item" in formatted
    assert "Second Item" in formatted


def test_format_empty_data():
    """Test formatting empty data list."""
    formatted = format_data_for_llm([])
    assert "No data found" in formatted


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
