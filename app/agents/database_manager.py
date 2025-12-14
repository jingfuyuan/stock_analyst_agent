from google.adk.agents import Agent
from google.adk.tools import google_search
from google.adk.models.google_llm import Gemini

from app.db.models import Watchlist, WatchlistMember, User, Ticker
from app.db.session import SessionLocal


def _normalize_ticker_symbols(tickers: list[str]) -> list[str]:
    """Deduplicate and clean ticker symbols."""
    normalized: list[str] = []
    for raw_symbol in tickers:
        symbol = raw_symbol.strip().upper() if raw_symbol else ""
        if symbol and symbol not in normalized:
            normalized.append(symbol)
    return normalized


def _ensure_tickers_exist(session, ticker_symbols: list[str]) -> list[str]:
    """Fetch or create the ticker rows that back a watchlist."""
    symbols = _normalize_ticker_symbols(ticker_symbols)
    for symbol in symbols:
        if session.get(Ticker, symbol) is None:
            session.add(Ticker(symbol=symbol))
    return symbols


def create_watchlist(user_id:int, watchlist_name: str, tickers: list[str], description: str) -> dict:
    """
    Use this function to create a watch list in the database for a user. 
    """
    with SessionLocal() as session:
        user = session.get(User, user_id)
        if user is None:
            raise ValueError(f"User {user_id} not found")

        existing = (
            session.query(Watchlist)
            .filter(Watchlist.user_id == user_id, Watchlist.name == watchlist_name)
            .first()
        )
        if existing:
            raise ValueError(f"Watchlist {watchlist_name} already exists for user {user_id}")

        ticker_symbols = _ensure_tickers_exist(session, tickers)
        watchlist_members = [
            WatchlistMember(ticker_symbol=symbol) for symbol in ticker_symbols
        ]
        watchlist = Watchlist(
            name=watchlist_name,
            description=description,
            user=user,
            members=watchlist_members
        )
        session.add(watchlist)
        session.commit()
        session.refresh(watchlist)
    
    return {
        "status": "success",
        "watchlist_id": watchlist.id
    }


def show_watchlist(user_id: int) -> dict:
    """
    Use this function to show all watchlists for a given user.
    """
    with SessionLocal() as session:
        user = session.get(User, user_id)
        if user is None:
            raise ValueError(f"User {user_id} not found")
        
        watchlists = session.query(Watchlist).filter(Watchlist.user_id == user_id).all()
        
        if not watchlists:
            return {"message": f"User {user_id} has no watchlists."}
        
        watchlist_data = []
        for watchlist in watchlists:
            members = []
            for member in watchlist.members:
                members.append(member.ticker_symbol)
            watchlist_data.append({
                "watchlist_name": watchlist.name,
                "description": watchlist.description,
                "tickers": members
            })
            
        return {
            "status": "success",
            "watchlists": watchlist_data
        }


def add_tickers_to_watchlist(user_id: int, watchlist_name: str, tickers: list[str]) -> dict:
    """
    Use this function to add tickers to an existing watchlist for a user.
    """
    with SessionLocal() as session:
        watchlist = session.query(Watchlist).filter(Watchlist.user_id == user_id, Watchlist.name == watchlist_name).first()
        if watchlist is None:
            raise ValueError(f"Watchlist {watchlist_name} not found for user {user_id}")
        
        ticker_symbols = _ensure_tickers_exist(session, tickers)

        existing_members = {
            member.ticker_symbol for member in watchlist.members
        }

        for ticker_symbol in ticker_symbols:
            if ticker_symbol not in existing_members:
                watchlist.members.append(
                    WatchlistMember(watchlist_id=watchlist.id, ticker_symbol=ticker_symbol)
                )
                existing_members.add(ticker_symbol)
                
        session.commit()
    
    return {
        "status": "success"
    }


def remove_tickers_from_watchlist(user_id: int, watchlist_name: str, tickers: list[str]) -> dict:
    """
    Use this function to remove tickers from an existing watchlist for a user.
    """
    with SessionLocal() as session:
        watchlist = session.query(Watchlist).filter(Watchlist.user_id == user_id, Watchlist.name == watchlist_name).first()
        if watchlist is None:
            raise ValueError(f"Watchlist {watchlist_name} not found for user {user_id}")
        
        ticker_symbols = _normalize_ticker_symbols(tickers)

        for ticker_symbol in ticker_symbols:
            watchlist_member = session.query(WatchlistMember).filter(
                WatchlistMember.watchlist_id == watchlist.id,
                WatchlistMember.ticker_symbol == ticker_symbol
            ).first()

            if watchlist_member:
                session.delete(watchlist_member)
                
        session.commit()
    
    return {
        "status": "success"
    }


watchlist_manger = Agent(
    name="watchlist_manager",
    model=Gemini(model="gemini-2.5-flash"),
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
    tools = [create_watchlist, show_watchlist, add_tickers_to_watchlist, remove_tickers_from_watchlist]
)
