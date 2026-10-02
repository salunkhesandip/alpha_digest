[1mdiff --git a/src/alpha_digest/prompts/prompts.py b/src/alpha_digest/prompts/prompts.py[m
[1mindex c913e45..014c110 100644[m
[1m--- a/src/alpha_digest/prompts/prompts.py[m
[1m+++ b/src/alpha_digest/prompts/prompts.py[m
[36m@@ -12,6 +12,7 @@[m [mSYSTEM_PROMPT = """You are a senior financial analyst AI that summarizes the lat[m
 3. Identify the most important stories, market-moving events, and sentiment.[m
 4. Group your analysis by ticker symbol.[m
 5. For each ticker, highlight:[m
[32m+[m[32m   - The current market price and day change, when available, in the ticker label or first sentence[m[41m[m
    - Key headlines and their potential market impact[m
    - Overall sentiment (bullish / bearish / neutral)[m
    - Any notable patterns across sources[m
[36m@@ -22,7 +23,8 @@[m [mSYSTEM_PROMPT = """You are a senior financial analyst AI that summarizes the lat[m
 - Be concise but insightful — target 2–3 paragraphs per ticker.[m
 - Use plain language; avoid jargon unless essential.[m
 - Cite specific headlines when referencing a story.[m
[31m-- Format each ticker label in bold, like **AAPL**.[m
[32m+[m[32m- Format each ticker label in bold, like **AAPL** or **AAPL — $220.50 (+1.25%)**.[m[41m[m
[32m+[m[32m- Include the current price and daily change when available, ideally in the ticker label.[m[41m[m
 - Do not use Markdown heading syntax like ### AAPL.[m
 """[m
 [m
[36m@@ -37,6 +39,7 @@[m [mHard rules:[m
 - Do not create separate sections for any other company, stock, ETF, or asset.[m
 - If another company is mentioned in an article, discuss it only within the section of the requested ticker whose news item included it.[m
 - If a requested ticker has no meaningful news (articles don't directly address its operations, performance, or strategy), OMIT it entirely from the summary.[m
[32m+[m[32m- Include the current price and day change in the ticker label or first sentence when available, e.g. **RCI — $42.15 (+1.75%)**.[m[41m[m
 - Write each ticker section label using bold text only, not ### headings.[m
 [m
 === STOCK NEWS TO ANALYZE ===[m
[36m@@ -59,8 +62,9 @@[m [mMerge them into a single cohesive financial digest that:[m
 3. Maintains ticker-by-ticker organization[m
 4. Uses only these ticker sections: {allowed_tickers}[m
 5. Does not create any section for unrequested companies or symbols[m
[31m-6. Formats each ticker section label as bold text like **AAPL**, not ### AAPL[m
[31m-7. OMITS any ticker that has no meaningful news or articles — do not include "no material news" sections[m
[32m+[m[32m6. Formats each ticker section label as bold text like **AAPL** or **AAPL — $220.50 (+1.25%)**, not ### AAPL[m[41m[m
[32m+[m[32m7. Includes the current price and day change in the ticker section when available[m[41m[m
[32m+[m[32m8. OMITS any ticker that has no meaningful news or articles — do not include "no material news" sections[m[41m[m
 [m
 Partial summaries:[m
 {partial_summaries}[m
