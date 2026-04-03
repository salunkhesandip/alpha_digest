# alpha_digest

A LangGraph AI agent for Stock Market Analysis

## Features

- **LangGraph Workflow**: Structured agent graph with fetch → format → process pipeline
- **LLM Integration**: Google Gemini for intelligent processing
- **Async Support**: Non-blocking async operations for better performance
- **Chunking**: Automatic chunking and merging for large inputs
- **Caching**: In-memory cache to avoid redundant API calls
- **Retry Logic**: Exponential back-off for resilient API calls

## Quick Start

1. Install `uv` if it is not already available:

	**Windows PowerShell**

	```powershell
	py -m pip install uv
	```

	**macOS / Linux (pip)**

	```bash
	python3 -m pip install uv
	```

	**macOS / Linux (recommended installer)**

	```bash
	curl -Ls https://astral.sh/uv/install.sh | sh
	```

2. Install project dependencies:

	```bash
	uv sync
	```

3. Copy `.env.example` to `.env` and add your API key.

4. Run the agent:

	```bash
	uv run python main.py --query "your input here"
	```

If you run without `--query` or `--tickers`, the agent uses the watchlist in `DEFAULT_TICKERS` inside `src/alpha_digest/config.py`.

For installation, environment configuration, and run commands, see [SETUP.md](SETUP.md).

## Project Structure

```
src/alpha_digest/
├── agent/           # Main agent graph and workflow
├── tools/           # Data source client and utilities
├── states/          # State definitions for the agent
├── prompts/         # LLM prompt templates
├── utils/           # Helper utilities (credentials)
└── tests/           # Unit tests
```

## Customization Guide

This project was generated from the **langgraph-agent-template**. Here's how to customize it for your use case:

### 1. Data Source (`tools/data_source.py`)
Replace the `fetch_data()` stub with your actual data fetching logic (API calls, database queries, web scraping, etc.).

### 2. State (`states/state.py`)
Add or modify fields in `AgentState` to hold the data your agent needs.

### 3. Prompts (`prompts/prompts.py`)
Customize `SYSTEM_PROMPT` and `SUMMARY_PROMPT_TEMPLATE` for your specific domain.

### 4. Graph (`agent/graph.py`)
Add new nodes, modify the workflow, or add conditional edges to the LangGraph pipeline.

### 5. Configuration (`config.py`)
Adjust limits, timeouts, retry settings, and the `DEFAULT_TICKERS` watchlist.
