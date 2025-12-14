# app/agents/daily_brief.py
from __future__ import annotations

from datetime import date, datetime
from typing import Dict, Any, List, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.session import SessionLocal
from app.db import models as m
from app.llm import generate_daily_brief_text
from app.services.tts import synthesize_speech


def _get_user_and_watchlists(db: Session, user_id: int) -> Tuple[m.User, List[m.Watchlist]]:
    user = db.get(m.User, user_id)
    if user is None:
        raise ValueError(f"User {user_id} not found")

    # Eager-load watchlists and members
    watchlists = (
        db.execute(
            select(m.Watchlist)
            .where(m.Watchlist.user_id == user_id)
            .order_by(m.Watchlist.id)
        )
        .scalars()
        .unique()
        .all()
    )
    return user, watchlists


def _get_watchlist_tickers(watchlists: List[m.Watchlist]) -> List[str]:
    symbols: set[str] = set()
    for wl in watchlists:
        for member in wl.members:
            if member.ticker_symbol:
                symbols.add(member.ticker_symbol)
    return sorted(symbols)


def _build_watchlist_snapshots(
    db: Session,
    watchlists: List[m.Watchlist],
    symbols: List[str],
    target_date: date,
) -> List[Dict[str, Any]]:
    """
    Build a list of per-ticker snapshots that contain:
    - basic price info
    - technical snapshot (MAs, RSI)
    - recent news & sentiment
    - which watchlists it belongs to
    """
    # Map symbol -> watchlists
    symbol_to_watchlists: Dict[str, List[str]] = {s: [] for s in symbols}
    for wl in watchlists:
        for member in wl.members:
            symbol_to_watchlists.setdefault(member.ticker_symbol, []).append(wl.name)

    snapshots: List[Dict[str, Any]] = []

    for symbol in symbols:
        ticker: m.Ticker | None = db.get(m.Ticker, symbol)
        if ticker is None:
            # Skip tickers that are not in ticker master table
            continue

        # Latest daily price (on or before target_date)
        dp: m.DailyPrice | None = (
            db.execute(
                select(m.DailyPrice)
                .where(
                    m.DailyPrice.ticker_symbol == symbol,
                    m.DailyPrice.date <= target_date,
                )
                .order_by(m.DailyPrice.date.desc())
                .limit(1)
            )
            .scalars()
            .first()
        )

        # Recent prices for basic changes (e.g. 5-day)
        recent_prices: List[m.DailyPrice] = (
            db.execute(
                select(m.DailyPrice)
                .where(
                    m.DailyPrice.ticker_symbol == symbol,
                    m.DailyPrice.date <= target_date,
                )
                .order_by(m.DailyPrice.date.desc())
                .limit(6)  # today + last 5 days
            )
            .scalars()
            .all()
        )

        # Simple % changes
        change_pct_day = None
        change_pct_week = None
        volume_vs_avg = None

        if len(recent_prices) >= 2 and dp and dp.close is not None:
            prev = recent_prices[1]
            if prev.close:
                change_pct_day = float(dp.close - prev.close) / float(prev.close) * 100.0

        if len(recent_prices) >= 6 and dp and dp.close is not None:
            week_ago = recent_prices[-1]
            if week_ago.close:
                change_pct_week = float(dp.close - week_ago.close) / float(week_ago.close) * 100.0

        if recent_prices:
            closes_volumes = [rp.volume for rp in recent_prices if rp.volume is not None]
            if dp and dp.volume is not None and closes_volumes:
                avg_vol = sum(closes_volumes) / len(closes_volumes)
                if avg_vol > 0:
                    volume_vs_avg = float(dp.volume) / float(avg_vol)

        # Technical snapshot for target_date
        tech: m.AnalysisSnapshot | None = (
            db.execute(
                select(m.AnalysisSnapshot)
                .where(
                    m.AnalysisSnapshot.ticker_symbol == symbol,
                    m.AnalysisSnapshot.date <= target_date,
                )
                .order_by(m.AnalysisSnapshot.date.desc())
                .limit(1)
            )
            .scalars()
            .first()
        )

        technicals = None
        if tech:
            technicals = {
                "ma_20": float(tech.ma_20) if tech.ma_20 is not None else None,
                "ma_50": float(tech.ma_50) if tech.ma_50 is not None else None,
                "ma_200": float(tech.ma_200) if tech.ma_200 is not None else None,
                "rsi_14": float(tech.rsi_14) if tech.rsi_14 is not None else None,
                "above_20dma": tech.above_20dma,
                "above_50dma": tech.above_50dma,
                "above_200dma": tech.above_200dma,
                "rsi_zone": tech.rsi_zone,
            }

        # Recent news (e.g. last 24–48h)
        news_items: List[m.NewsItem] = (
            db.execute(
                select(m.NewsItem)
                .where(
                    m.NewsItem.ticker_symbol == symbol,
                    m.NewsItem.published_at >= datetime.combine(target_date, datetime.min.time()),
                )
                .order_by(m.NewsItem.published_at.desc())
                .limit(5)
            )
            .scalars()
            .all()
        )

        news_payload = [
            {
                "headline": n.headline,
                "sentiment_label": n.sentiment_label,
                "sentiment_score": float(n.sentiment_score) if n.sentiment_score is not None else None,
                "published_at": n.published_at.isoformat(),
                "source": n.source,
            }
            for n in news_items
        ]

        # Simple daily sentiment aggregation
        if news_items:
            scores = [float(n.sentiment_score) for n in news_items if n.sentiment_score is not None]
        else:
            scores = []

        daily_sentiment = None
        if scores:
            daily_sentiment = {
                "avg_score": sum(scores) / len(scores),
                "num_articles": len(scores),
            }

        snapshot = {
            "ticker": symbol,
            "name": ticker.name,
            "watchlists": symbol_to_watchlists.get(symbol, []),
            "price": {
                "close": float(dp.close) if dp and dp.close is not None else None,
                "change_pct_day": change_pct_day,
                "change_pct_week": change_pct_week,
                "volume_vs_avg": volume_vs_avg,
            },
            "technicals": technicals,
            "news": news_payload,
            "daily_sentiment": daily_sentiment,
        }
        snapshots.append(snapshot)

    return snapshots


def _build_market_overview(db: Session, target_date: date) -> Dict[str, Any]:
    """
    Placeholder: query whatever tables or external API summary you build later.
    For MVP, you can hardcode or store index data in tickers/daily_prices.
    """
    # Example assuming you store ^GSPC, ^IXIC, ^DJI as tickers:
    indexes = []
    for symbol, name in [("^GSPC", "S&P 500"), ("^IXIC", "Nasdaq"), ("^DJI", "Dow Jones")]:
        dp: m.DailyPrice | None = (
            db.execute(
                select(m.DailyPrice)
                .where(
                    m.DailyPrice.ticker_symbol == symbol,
                    m.DailyPrice.date <= target_date,
                )
                .order_by(m.DailyPrice.date.desc())
                .limit(1)
            )
            .scalars()
            .first()
        )
        prev: m.DailyPrice | None = (
            db.execute(
                select(m.DailyPrice)
                .where(
                    m.DailyPrice.ticker_symbol == symbol,
                    m.DailyPrice.date < target_date,
                )
                .order_by(m.DailyPrice.date.desc())
                .limit(1)
            )
            .scalars()
            .first()
        )

        change_pct = None
        if dp and prev and dp.close is not None and prev.close is not None:
            change_pct = float(dp.close - prev.close) / float(prev.close) * 100.0

        if dp:
            indexes.append(
                {
                    "name": name,
                    "symbol": symbol,
                    "change_pct": change_pct,
                    "close": float(dp.close) if dp.close is not None else None,
                    "highlights": [],
                }
            )

    # For MVP, you can leave sectors/macro_events empty or fill manually.
    return {
        "indexes": indexes,
        "sectors": [],
        "macro_events": [],
    }


def run_daily_brief(user_id: int, target_date: date | None = None) -> m.Brief:
    """
    Orchestrate the daily brief generation:
    - loads user & watchlists
    - builds context from DB (prices, technicals, news)
    - calls LLM to generate text
    - optionally TTS
    - stores Brief row
    """
    if target_date is None:
        target_date = date.today()

    db: Session = SessionLocal()
    try:
        user, watchlists = _get_user_and_watchlists(db, user_id)
        symbols = _get_watchlist_tickers(watchlists)

        market_overview = _build_market_overview(db, target_date)
        watchlist_snapshots = _build_watchlist_snapshots(db, watchlists, symbols, target_date)

        context = {
            "date": target_date.isoformat(),
            "user": {
                "name": user.name or "Investor",
                "timezone": user.timezone,
                "watchlists": [
                    {
                        "name": wl.name,
                        "tickers": [memb.ticker_symbol for memb in wl.members],
                    }
                    for wl in watchlists
                ],
                "preferences": {
                    "style": "concise",
                    "focus": ["watchlist", "news", "technicals"],
                },
            },
            "market_overview": market_overview,
            "watchlist_snapshots": watchlist_snapshots,
        }

        # --- LLM call ---
        brief_text = generate_daily_brief_text(context=context)

        # --- TTS (optional) ---
        audio_path = None
        if user.tts_enabled:
            audio_path = synthesize_speech(brief_text)

        # Upsert Brief row for this user/date
        existing_brief: m.Brief | None = (
            db.execute(
                select(m.Brief)
                .where(m.Brief.user_id == user.id, m.Brief.date == target_date)
            )
            .scalars()
            .first()
        )

        if existing_brief:
            existing_brief.text = brief_text
            existing_brief.audio_path = audio_path
            existing_brief.created_at = datetime.utcnow()
            brief = existing_brief
        else:
            brief = m.Brief(
                user_id=user.id,
                date=target_date,
                text=brief_text,
                audio_path=audio_path,
            )
            db.add(brief)

        db.commit()
        db.refresh(brief)

        return brief

    finally:
        db.close()
