"""Configuration and constants for the alpha_digest agent."""

import logging
import os
from datetime import datetime

# ── Logging ──────────────────────────────────────────────────────────────
_log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_handlers: list[logging.Handler] = [logging.StreamHandler()]

_log_file = os.getenv("LOG_FILE")
if _log_file:
    _ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    _base, _ext = os.path.splitext(_log_file)
    _log_file = f"{_base}_{_ts}{_ext or '.log'}"
    if os.path.dirname(_log_file):
        os.makedirs(os.path.dirname(_log_file), exist_ok=True)
    _handlers.append(logging.FileHandler(_log_file, mode="a", encoding="utf-8"))

logging.basicConfig(
    level=logging.INFO,
    format=_log_format,
    handlers=_handlers,
)
logger = logging.getLogger("alpha_digest")

# LLM Configuration
DEFAULT_LLM_MODEL = "models/gemini-2.5-flash"
DEFAULT_TEMPERATURE = 0.7

# Processing Configuration
DEFAULT_ITEM_LIMIT = 20
MAX_ITEM_LIMIT = 100

# Chunking – max blocks per LLM call before we chunk-and-merge
# Increased to 150: 132 blocks at ~578 chars avg ≈ 76K chars ≈ 20K tokens,
# well within Gemini 2.5 Flash's 1M-token context window.
CHUNK_SIZE = 150

# Retry configuration
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2  # exponential back-off base in seconds

# Prompt Templates
DEFAULT_SUMMARY_LENGTH = "3-7 paragraphs"

# Timeouts (in seconds)
API_TIMEOUT = 30
LLM_TIMEOUT = 60

# Cache TTL (seconds)
CACHE_TTL = 300  # 5 minutes

# Error Messages
MISSING_API_KEY_ERROR = (
    "Missing Google API key. Please set GOOGLE_API_KEY environment variable."
)

# ── Finnhub ───────────────────────────────────────────────────────────────
FINNHUB_BASE_URL = "https://finnhub.io/api/v1"
DEFAULT_LOOKBACK_DAYS = 1
DEFAULT_NEWS_PER_TICKER = 30

# Relevance filtering — Finnhub's "related" field is very broad, so many
# returned articles are only tangentially related to the queried ticker.
# Articles below this score are dropped.  Set to 0.0 to disable filtering.
MIN_RELEVANCE_SCORE = float(os.getenv("ALPHA_DIGEST_MIN_RELEVANCE", "0.15"))

# Ticker list configuration
# Edit this list directly to change the default watchlist used when no
# --tickers/--query argument is provided.
DEFAULT_TICKERS: list[str] = [
    # Magnificent 7 stocks
    "AAPL",
    "MSFT",
    "GOOGL",
    "AMZN",
    "NVDA",
    "TSLA",
    "META",
    # Additional tickers
    "TEVA",
    "SEDG",
    "INTC",
    "M",
    "PHG",
    "T",
    "ERIC",
    "BAC",
    "CSIQ",
    "CVS",
    "RIVN",
    "AEO",
    "RCI",
    "PLUG",
    "KVUE",
    "BMY",
    "ABEV",
    "HPQ",
    "TELFY",
    "BCE",
    "KSS",
    "PFE",
    "STLA",
    "TU",
    "LYFT",
    "TRIP",
    "CMCSA",
    "YEXT",
    "KHC",
    "TDOC",
    "GRFS",
    "SNAP",
    "PAYX",
    "CHWY",
    "MRNA",
    "EVRG",
    "PATH",
    "HMC",
    "VSNT",
    "FIG",
    "AVTR",
]
