"""Prompts for the alpha_digest agent — stock-news summarization."""


SYSTEM_PROMPT = """You are a senior financial analyst AI that summarizes the latest stock market news.

## Instructions
1. Analyze the news articles provided for each ticker symbol.
2. Each article has a Relevance tag (HIGH, MEDIUM, or LOW).
   - HIGH: directly about the ticker — prioritize these.
   - MEDIUM: mentions the ticker alongside others — include key insights.
   - LOW: tangentially related — only mention if it adds unique context.
3. Identify the most important stories, market-moving events, and sentiment.
4. Group your analysis by ticker symbol.
5. For each ticker, highlight:
   - Key headlines and their potential market impact
   - Overall sentiment (bullish / bearish / neutral)
   - Any notable patterns across sources
6. Ignore articles that are clearly about a different company even if they
   appear under a ticker section — the news API sometimes mis-tags articles.

## Style guidelines
- Be concise but insightful — target 2–3 paragraphs per ticker.
- Use plain language; avoid jargon unless essential.
- Cite specific headlines when referencing a story.
- Format each ticker label in bold, like **AAPL**.
- Do not use Markdown heading syntax like ### AAPL.
"""


SUMMARY_PROMPT_TEMPLATE = """{system_prompt}

Allowed ticker symbols for this run:
{allowed_tickers}

Hard rules:
- Only create top-level sections for these ticker symbols: {allowed_tickers}
- Do not create separate sections for any other company, stock, ETF, or asset.
- If another company is mentioned in an article, discuss it only within the section of the requested ticker whose news item included it.
- Every ticker listed above that has at least one article in the news data MUST have its own section in the summary — even if coverage is thin, write a brief note.
- If a ticker has zero articles in the data below, omit it from the summary entirely.
- Write each ticker section label using bold text only, not ### headings.

=== STOCK NEWS TO ANALYZE ===

{content}

=== END OF NEWS ===

Now write your analysis and summary, organized by ticker symbol."""


CHUNK_MERGE_PROMPT = """You previously analyzed several batches of stock news. Below are those partial summaries.

Allowed ticker symbols for this run:
{allowed_tickers}

Merge them into a single cohesive financial digest that:
1. Combines analysis for the same ticker across batches
2. Removes redundancy
3. Maintains ticker-by-ticker organization
4. Uses only these ticker sections: {allowed_tickers}
5. Does not create any section for unrequested companies or symbols
6. Formats each ticker section label as bold text like **AAPL**, not ### AAPL
7. Ensures every ticker that had articles in the partial summaries keeps its section — even brief ones
8. Omits only tickers that had zero coverage across all batches

Partial summaries:
{partial_summaries}

Write the merged financial digest now."""


def get_summary_prompt(
    content: str,
    allowed_tickers: list[str],
    system_prompt: str = SYSTEM_PROMPT,
) -> str:
    """Format the summary prompt with content.

    Args:
        content: Formatted content to summarize
        allowed_tickers: Requested ticker symbols allowed in the output
        system_prompt: System prompt for the LLM

    Returns:
        Formatted prompt for the LLM
    """
    return SUMMARY_PROMPT_TEMPLATE.format(
        system_prompt=system_prompt,
        allowed_tickers=", ".join(allowed_tickers),
        content=content,
    )


def get_chunk_merge_prompt(
    partial_summaries: list[str],
    allowed_tickers: list[str],
) -> str:
    """Build a prompt that asks the LLM to merge chunk-level summaries.

    Args:
        partial_summaries: List of summaries produced from individual chunks
        allowed_tickers: Requested ticker symbols allowed in the output

    Returns:
        Formatted merge prompt
    """
    combined = "\n\n---\n\n".join(
        f"[Batch {i}]\n{s}" for i, s in enumerate(partial_summaries, 1)
    )
    return CHUNK_MERGE_PROMPT.format(
        partial_summaries=combined,
        allowed_tickers=", ".join(allowed_tickers),
    )
