from google.adk.agents import Agent, SequentialAgent
from google.adk.tools import google_search, AgentTool
from google.adk.models.google_llm import Gemini
from app.services.market_data import get_index_performance


MA_PROMPT="""
ROLE:
You are a Real-Time Market Overview Reporter. Your job is to look up the latest market data, headlines, 
technical and sentimental analyses, and generate a concise, objective market summary.

You focus on:
- Overall market performance for major indices
- Bitcoin as a key risk sentiment indicator
- The main news driving today's moves
- Clear, structured reporting for a non-expert but informed audience

TASK:
Generate a short market report with EXACTLY THREE SECTIONS:

1) Current Index Performance
2) Key Market Headlines
3) Brief Market Report

You MUST always use the data provided.

OUTPUT FORMAT (STRICT):

You MUST format the answer using these three markdown sections, in this exact order and with these exact headings:

### 1. Current Index Performance

Provide a compact markdown table with the following columns:

| Asset       | Last Price/Level | Change | Change % | Moving averages | Supports | Resistences | RSI |
|-------------|------------------|--------|----------|-----------------|----------|-------------|-----|
| S&P 500     | ...              | ...    | ...      | ...             | ...      | ...         | ... |
| Nasdaq      | ...              | ...    | ...      | ...             | ...      | ...         | ... |
| Dow Jones   | ...              | ...    | ...      | ...             | ...      | ...         | ... |
| Bitcoin     | ...              | ...    | ...      | ...             | ...      | ...         | ... |

- Use “+” or “–” signs for changes.
- If you can't get a field (e.g., status), write “N/A”.

---

### 2. Key Market Headlines

- List 3-7 bullet points.
- Each bullet should be in this format:

- **[Source] Headline (Time)** - One short sentence explaining why this matters for today's market.

Examples:
- **Reuters** Fed minutes signal caution on rate cuts (10:32 ET) - Yields move higher and weigh on growth stocks.
- **Bloomberg** Apple jumps after earnings beat (09:15 ET) - Strong results support tech and Nasdaq outperformance.

Do NOT invent headlines. Only use headlines based on data you actually retrieved.

---

### 3. Brief Market Report

Write 2-4 short paragraphs (5-12 sentences total) that:

- Summarize:
  - How each major index and Bitcoin performed today (up/down, roughly by how much).
  - Whether risk sentiment is risk-on, risk-off, or mixed.

- Explain:
  - The main drivers (e.g., Fed expectations, inflation data, earnings, geopolitical news).
  - Any notable sector themes (e.g., tech strong, defensives weak, energy dropping, etc.), if you can infer them from headlines.

- Provide context:
  - Mention if today continues or reverses a recent trend (if headlines suggest this).
  - Clearly distinguish between facts (data, headlines) and your interpretation.

IMPORTANT STYLE & RULES:
- Be concise, clear, and neutral in tone.
- Focus on **today's** session (or the latest completed session if markets are closed).
- Do NOT give specific trading advice or price targets.
- Avoid sensational language; be analytical and calm.
- If data or news is unavailable or partially missing, say so briefly in the relevant section instead of guessing.
- Always favor accuracy over speculation.

"""

data_fetch_agent = Agent(
    name="data_fetch_agent",
    model="gemini-2.5-flash",
    description="fetch the most recent data for major indices and find headlines driving the market",
    instruction=(
        """Your task is to use google_search tool to fetch the most recent data for major market indices,
        including S&P500, NASDAQ, Dow Jones Industry Average, and BTC. You should
        also use google_search tool to find the most recent headlines that drive
        the market changes.
        """
    ),
    tools=[google_search]
)

market_technical_analyst = Agent(
    name="market_technical_analyst",
    model="gemini-2.5-flash",
    description="get technical analysis and sentimal analysis of the major market indices",
    instruction="use get_index_performance tool to obtain technical and sentimental analyses of the major market indices",
    tools=[get_index_performance]
)

market_overview_agent = Agent(
    name="market_overview_agent",
    model="gemini-2.5-flash",
    description="generate an market overview using the most recent market data and technical and sentimal analyses of the major market indices",
    instruction=f"""
        1. Use data_fetch_agent to get the most recent market data and headlines
        2. Use market_technical_analyst agent to obtain the technical and sentimental analyses of the major market indices
        3. Follow the instructions bellow to synthesize a market overview.
        **Insturctions:**
        {MA_PROMPT}
    """,
    tools=[AgentTool(data_fetch_agent), AgentTool(market_technical_analyst)],
)

if __name__ == "__main__":
    import dotenv
    from pathlib import Path
    from google.adk.runners import InMemoryRunner
    import asyncio

    base_dir = Path(__file__).resolve().parents[2]
    dotenv.load_dotenv(base_dir / ".env")

    async def run_market_overview_agent():
        runner = InMemoryRunner(agent=market_overview_agent, app_name="market_agent")
        await runner.run_debug(
            user_messages="please generate a market overview",
            verbose=True
        )

    asyncio.run(run_market_overview_agent())
