from google.adk.agents import Agent
from google.adk.tools import google_search
from app.db.models import Watchlist, WatchlistMember, User, Ticker
from app.db.session import SessionLocal

def create_watchlist(user_id:int, watchlist_name: str, tickers: list[str], description: str) -> dict:
    """
    Use this function to create a watch list in the database for a user. 
    """
    with SessionLocal() as session:
        user = session.get(User, user_id)
        if user is None:
            raise ValueError(f"User {user_id} not found")
        tickers_list = [Ticker(symbol) for symbol in tickers]
        watchlist_members = [WatchlistMember(ticker_symbol=ticker.symbol) for ticker in tickers_list]
        watchlist = Watchlist(
            name=watchlist_name,
            description=description,
            user=user,
            members=watchlist_members
        )
        session.add(watchlist)
        session.commit()
    
    return {
        "status": "success"
    }


watchlist_manger = Agent(
    name="watchlist_manager",
    model="gemini-2.5-flash",
    description="help users to manage their stock watch lists",
    instruction=(
        """You are a helpful agent who can help users to manage their stock watch list. You can use 
         the provided tools to do the following operations:
          1. help users to create watch list using the `create_watchlist` tool.
          2. show users their watch list using the `show_watchlist` tool.
          3. add tickers into user's watch list using the `add_tickers_to_watchlist` tool.
          4. remove tickers from user's watch list using the `remove_tickers_from_watchlist` tool. 
          5. when users provide company names, you can use `google_search` to find the ticker symbols.
          6. if ticker symbols are provided, you can use `google_seach` to find the company names and confirm with
          users.
        You should be very interactive with the users. When you need necessary information for these operations,
          do not make up anything. You should ask users directly. 
          """
    ),
    tools = []
)