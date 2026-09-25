# Setup Guide for alpha_digest

This guide covers local setup, environment configuration, running the agent, and the first files you will likely customize.

**Quick links:** [Prerequisites](#prerequisites) | [Install `uv`](#install-uv) | [Install dependencies](#install-dependencies) | [Configure credentials](#configure-environment-variables) | [Run the agent](#run-the-agent) | [Troubleshooting](#troubleshooting) | [Next steps](#next-steps)

## Prerequisites

- Python 3.12 or newer
- `pip` available in your shell
- `uv` installed (the project dependency manager)
- An API key for Google Gemini

## Install `uv`

### Windows PowerShell

```powershell
py -m pip install --upgrade pip
py -m pip install uv
```

Verify: `uv --version`

### macOS or Linux (via pip)

```bash
python3 -m pip install --upgrade pip
python3 -m pip install uv
```

Verify: `uv --version`

### macOS or Linux (recommended installer)

```bash
curl -Ls https://astral.sh/uv/install.sh | sh
```, create a virtual environment and install dependencies:

```bash
uv sync
```

This creates `.venv/` and installs all dependencies from `pyproject.toml`.

To also install development tools (`pytest`, `black`, `isort`, `mypy`):

```bash
uv sync --extra dev
```

Verify: `uv run python -c "import langgraph; print('LangGraph installed')"`

If you want development tools such as `pytest`, `black`, `isort`, and `mypy`:

```bash
uv sync --extra dev
```the template:

### Windows PowerShell

```powershell
Copy-Item .env.example .env
```

### macOS or Linux

```bash
cp .env.example .env
```

Open `.env` in your editor and fill in required credentials:

**Required:**

- `GOOGLE_API_KEY`: Get from [Google AI Studio](https://makersuite.google.com/app/apikey)
- Default tickers come from `DEFAULT_TICKERS` in `src/alpha_digest/config.py`

**Optional:**

- `LOG_FILE=logs/agent.log` — write logs to disk in addition to console
- `LANGCHAIN_TRACING_V2=true` — enable LangSmith observability

Optional:

- set `LOG_FILE=logs/agent.log` to also write logs to disk
All commands use `uv run` to execute in the managed environment.

Run with a custom query:

```bash
uv run python main.py --query "your input here"
```

Run with default settings:

```bash
uv run python main.py

```bash
uv run python main.py --query "your input here"
```

## Run Tests

```bash
uv run pytest src/alpha_digest/tests -v
```

## First Customization Steps

This generated project is a scaffold. In most cases you should update these areas first:

1. `src/alpha_digest/tools/data_source.py`
2. `src/alpha_digest/states/state.py`
3. `src/alpha_digest/prompts/prompts.py`
4. `src/alpha_digest/agent/graph.py`
5. `src/alpha_digest/config.py`

## Troubleshooting

### `uv` command not found

- Close and reopen your terminal to refresh PATH.
- If still missing, reinstall `uv` and follow the PATH setup instructions from the installer.

### Missing API key error

```
ValueError: Please set GOOGLE_API_KEY environment variable
```

- Verify `.env` exists in the project root.
- Check that the key value is correct (no extra quotes or spaces).
- Reload your shell environment.

### Python version mismatch

If `uv sync` fails with a Python version error:

- Check your Python version: `python --version`
- Install Python 3.12+ if needed before running `uv sync`.

### Dependency installation issues

To refresh the lock file and reinstall:

```bash
uv sync --refresh
```

### Test command cannot find the package

- Ensure you are running from the project root: `ls pyproject.toml`
- Verify the package folder exists: `ls src/alpha_digest/`

## Next Steps

**Before running the agent, customize these files:**

1. **Data source** — `src/alpha_digest/tools/data_source.py`  
   Replace the stub `fetch_data()` with your actual data source.

2. **State** — `src/alpha_digest/states/state.py`  
   Add fields to hold your domain-specific data.

3. **Prompts** — `src/alpha_digest/prompts/prompts.py`  
   Customize `SYSTEM_PROMPT` and `SUMMARY_PROMPT_TEMPLATE`.

4. **Graph** — `src/alpha_digest/agent/graph.py`  
   Modify nodes, add conditional edges, or integrate external tools.

5. **Config** — `src/alpha_digest/config.py`  
   Adjust timeouts, retry limits, and other tuning parameters.

**See also:** [README.md](README.md) for feature overview and project structure.