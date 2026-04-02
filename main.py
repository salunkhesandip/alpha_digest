"""Main entry point for the alpha_digest agent."""

import asyncio
import argparse
from typing import Optional
from dotenv import load_dotenv

# Load environment variables BEFORE importing config so LOG_FILE is available
load_dotenv()

import time
import logging
logging.getLogger("httpx").setLevel(logging.WARNING)
from src.alpha_digest.config import logger
logger.info(f"Program started at {time.strftime('%Y-%m-%d %H:%M:%S')}")
from src.alpha_digest.agent import run_agent


async def main(tickers: Optional[str] = None) -> None:
    """Run the alpha_digest agent.

    Args:
        tickers: Comma-separated ticker symbols (e.g. "AAPL,MSFT,TSLA").
    """

    if tickers:
        logger.info(f"Running agent with tickers: {tickers}")
    else:
        logger.info("Running agent with default configuration...")

    result = await run_agent(query=tickers)

    if result["error"]:
        logger.error(f"Error: {result['error']}")
        logger.info(f"Program ended at {time.strftime('%Y-%m-%d %H:%M:%S')}")
        return

    logger.info("RESULT:\n" + (result.get("summary") or "No summary generated."))

    if result.get("email_status"):
        logger.info(f"Email status: {result['email_status']}")
    if result.get("telegram_status"):
        logger.info(f"Telegram status: {result['telegram_status']}")
    if result.get("audio_path"):
        logger.info(f"Audio file: {result['audio_path']}")

    logger.info(f"Program ended at {time.strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="A LangGraph AI agent for Stock Market News Analysis"
    )
    parser.add_argument(
        "--tickers",
        type=str,
        help="Comma-separated ticker symbols (e.g. AAPL,MSFT,TSLA)",
        default=None,
    )
    # Keep --query as alias for --tickers for backward compatibility
    parser.add_argument(
        "--query",
        type=str,
        help="Alias for --tickers",
        default=None,
    )

    args = parser.parse_args()
    tickers = args.tickers or args.query

    asyncio.run(main(tickers=tickers))
