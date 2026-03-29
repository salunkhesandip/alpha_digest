"""Prompts for the alpha_digest agent.

TODO: Customize these prompts for your specific use case.
"""


SYSTEM_PROMPT = """You are an expert AI assistant that processes and summarizes information.

## Instructions
1. Carefully analyze the provided content.
2. Identify the key themes and important points.
3. Organize the information into logical groups.
4. Write a clear, concise summary.

## Style guidelines
- Keep the summary between 3 and 7 paragraphs.
- Write in a conversational yet concise tone.
- Avoid simply listing items one by one; synthesize related information.
"""


SUMMARY_PROMPT_TEMPLATE = """{system_prompt}

=== CONTENT TO PROCESS ===

{content}

=== END OF CONTENT ===

Now write a clear summary of the content above. Organize by themes and highlight the most important points."""


CHUNK_MERGE_PROMPT = """You previously processed several batches of content. Below are those partial summaries.

Merge them into a single cohesive summary that:
1. Combines overlapping themes
2. Removes redundancy
3. Maintains a logical flow

Partial summaries:
{partial_summaries}

Write the merged summary now."""


def get_summary_prompt(content: str, system_prompt: str = SYSTEM_PROMPT) -> str:
    """Format the summary prompt with content.

    Args:
        content: Formatted content to summarize
        system_prompt: System prompt for the LLM

    Returns:
        Formatted prompt for the LLM
    """
    return SUMMARY_PROMPT_TEMPLATE.format(
        system_prompt=system_prompt,
        content=content,
    )


def get_chunk_merge_prompt(partial_summaries: list[str]) -> str:
    """Build a prompt that asks the LLM to merge chunk-level summaries.

    Args:
        partial_summaries: List of summaries produced from individual chunks

    Returns:
        Formatted merge prompt
    """
    combined = "\n\n---\n\n".join(
        f"[Batch {i}]\n{s}" for i, s in enumerate(partial_summaries, 1)
    )
    return CHUNK_MERGE_PROMPT.format(partial_summaries=combined)
