"""Shared pytest fixtures and configuration."""

import pytest


@pytest.fixture
def agent_state():
    """Return a minimal AgentState dict for testing."""
    return {"query": "test"}
