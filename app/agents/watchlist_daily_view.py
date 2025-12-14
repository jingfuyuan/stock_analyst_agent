from google.adk.agents import Agent, SequentialAgent
from google.adk.tools import google_search, AgentTool
from google.adk.models.google_llm import Gemini
from app.services.technicals import technical_analysis
from app.services.news import sentimental_analysis
from typing import List, Dict

# Use a fixed watchlist for now. To do: Need to fetch watchlist from the database
WATCHLIST = ["AMD", "NVDA", "META", "TSLA", "AMZN"]


watchlist_viewer = Agent(
    name="watchlist_viewer",
    model="gemini-2.5-flash",
    description="generate a quick view of each stock in the watchlist",
    instruction="""
        You will be provided a watchlist of stocks. Your task is to generate a quick view of each stock in 
        the watchlist. Use technical_analysis and sentimental_analysis tools to get information for each stock
        and make a brief summary for each stock.
    """,
    tools=[technical_analysis, sentimental_analysis]
)

if __name__ == "__main__":
    import dotenv
    from pathlib import Path
    from google.adk.runners import InMemoryRunner
    import asyncio

    base_dir = Path(__file__).resolve().parents[2]
    dotenv.load_dotenv(base_dir / ".env")

    async def run_market_overview_agent():
        runner = InMemoryRunner(agent=watchlist_viewer, app_name="watchlist_viewer")
        await runner.run_debug(
            user_messages=f"please generate a quick view of my watchlist: {','.join(WATCHLIST)}",
            verbose=True
        )

    asyncio.run(run_market_overview_agent())