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


async def main(query: Optional[str] = None) -> None:
    """Run the alpha_digest agent.

    Args:
        query: Optional input query or parameter for the agent.
    """

    if query:
        logger.info(f"Running agent with query: {query}")
    else:
        logger.info("Running agent with default configuration...")

    result = await run_agent(query=query)

    if result["error"]:
        logger.error(f"Error: {result['error']}")
        logger.info(f"Program ended at {time.strftime('%Y-%m-%d %H:%M:%S')}")
        return

    logger.info("RESULT:\n" + (result.get("summary") or "No summary generated."))

    logger.info(f"Program ended at {time.strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="A LangGraph AI agent for Stock Market Analysis"
    )
    parser.add_argument(
        "--query",
        type=str,
        help="Input query or parameter for the agent",
        default=None,
    )

    args = parser.parse_args()

    asyncio.run(main(query=args.query))
