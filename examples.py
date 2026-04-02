"""alpha_digest examples — Finnhub company-news summarization."""

from dotenv import load_dotenv

load_dotenv()

from src.alpha_digest.agent import create_agent_graph
from src.alpha_digest.states import AgentState


def example_basic_usage():
    """Fetch last-day news for AAPL and MSFT, then summarize."""
    agent = create_agent_graph()

    initial_state: AgentState = {"query": "AAPL,MSFT"}

    result = agent.invoke(initial_state)

    if result.get("error"):
        print(f"Error: {result['error']}")
    else:
        print("\n=== News Summary ===")
        print(result.get("summary"))


def example_multiple_tickers():
    """Fetch last-day news for several tech tickers."""
    agent = create_agent_graph()

    initial_state: AgentState = {"query": "AAPL,MSFT,TSLA,GOOGL,AMZN"}

    result = agent.invoke(initial_state)

    if result.get("error"):
        print(f"Error: {result['error']}")
    else:
        print("\n=== Multi-Ticker News Digest ===")
        print(result.get("summary"))


if __name__ == "__main__":
    print("Example 1: Basic usage (AAPL, MSFT)")
    print("-" * 50)
    # Uncomment to run (requires .env with FINNHUB_API_KEY and GOOGLE_API_KEY):
    # example_basic_usage()

    print("\nExample 2: Multiple tickers")
    print("-" * 50)
    # example_multiple_tickers()
