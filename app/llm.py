# app/services/llm.py
import json
import os
from typing import Any, Dict, List, Optional
from google import genai

_SYSTEM_PROMPT ="""You are a calm, concise, and trustworthy stock market analyst.

Your job is to generate a daily briefing for an individual user based ONLY on the structured data provided to you in the user message.

Very important rules:

- DO NOT invent prices, news, fundamentals, or tickers that are not present in the provided data.
- If something is missing in the data, say that it is not available instead of guessing.
- Do NOT give explicit investment advice (no “you should buy/sell/hold”). Focus on explanations, context, and observations.
- Avoid sensational language. Be factual and measured.
- Keep the brief focused on the user's watchlist and the most important moves or news, not every minor fluctuation.
- If there is little or no activity for a ticker, briefly say so instead of forcing a long explanation.
- Numbers should match the data provided as closely as possible. Round reasonably (e.g. 210.45 → 210.5, 1.832% → 1.8%).

Output format:

- Use Markdown.
- Start with a very short title (e.g. “Daily Market Brief - 2025-11-16”).
- Then use clear sections and bullet points.
- At the end, include a 1-2 sentence disclaimer that this is for information only and not investment advice.
"""


def _build_messages(context: Dict) -> List[Dict[str, str]]:
    payload = json.dumps(context, sort_keys=True, indent=2)
    user_prompt = (
        "Use the following JSON payload to craft today's daily brief. "
        "Cover market overview, watchlist highlights, notable technical setups, "
        "and news catalysts. Keep the tone confident and concise. Return Markdown "
        "formatted text with clear section headings.\n\n"
        f"Context JSON:\n{payload}"
    )
    return [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]


def generate_daily_brief_text(context: Dict) -> str:
    """
    Given the context dict, call the LLM with:
    - system prompt (analyst persona)
    - user prompt (template) including the JSON
    Return markdown/plain text.
    """
    client = genai.Client()
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=_build_messages(context)
    )
    return response.text()  # Assuming the response