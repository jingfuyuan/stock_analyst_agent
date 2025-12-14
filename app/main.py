from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.db.session import Base, engine
# from app.db import models
from app.db.session import SessionLocal
from app.db.models import User, Watchlist, WatchlistMember, Ticker
import asyncio
import dotenv
from app.agents.database_manager import watchlist_manger
from app.agents import database_manager as dm
from google.adk.runners import InMemoryRunner
from app.agents.market_overview import market_overview_agent, data_fetch_agent

dotenv.load_dotenv(Path(__file__).resolve().parent.parent / ".env")

def init_db():
    Base.metadata.create_all(bind=engine)

async def debug_watchlist_agent() -> None:
    runner = InMemoryRunner(agent=watchlist_manger, app_name="agents")
    await runner.run_debug(
        "my user id is 1. Can you add AMZN into my Tech stocks watch list",
        verbose=True,
    )

async def run_market_overview_agent():
    runner = InMemoryRunner(agent=data_fetch_agent, app_name="market_agent")
    await runner.run_debug(
        user_messages="please generate a market overview",
        verbose=True
    )

if __name__ == "__main__":
    # init_db()
    # with SessionLocal() as session:
    #     user = User(
    #         id=2,
    #         email="jingfuyuan@x.com",
    #         name="Fuyuan Jing",
    #         tts_enabled=False
    #     )
    #     session.add(user)
    #     session.commit()

    # test watchlist_manager agent
    asyncio.run(run_market_overview_agent())
    # watchlist_manger.run()
    # dm.create_watchlist(user_id=1, watchlist_name="Tech stocks", tickers=["TSLA", "MSFT"], description="big tech")
