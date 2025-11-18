# app/db/models.py
from datetime import datetime, date
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    Date,
    ForeignKey,
    Numeric,
    Text,
    JSON,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from .session import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    timezone: Mapped[str] = mapped_column(String, default="America/New_York")
    brief_time_local: Mapped[str | None] = mapped_column(String, nullable=True)  # "08:00"
    tts_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    watchlists: Mapped[list["Watchlist"]] = relationship("Watchlist", back_populates="user")
    briefs: Mapped[list["Brief"]] = relationship("Brief", back_populates="user")


class Ticker(Base):
    __tablename__ = "tickers"

    symbol: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    exchange: Mapped[str | None] = mapped_column(String, nullable=True)
    sector: Mapped[str | None] = mapped_column(String, nullable=True)
    industry: Mapped[str | None] = mapped_column(String, nullable=True)
    currency: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    daily_prices: Mapped[list["DailyPrice"]] = relationship("DailyPrice", back_populates="ticker")
    analysis_snapshots: Mapped[list["AnalysisSnapshot"]] = relationship(
        "AnalysisSnapshot", back_populates="ticker"
    )
    news_items: Mapped[list["NewsItem"]] = relationship("NewsItem", back_populates="ticker")


class Watchlist(Base):
    __tablename__ = "watchlists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )

    user: Mapped["User"] = relationship("User", back_populates="watchlists")
    members: Mapped[list["WatchlistMember"]] = relationship(
        "WatchlistMember", back_populates="watchlist", cascade="all, delete-orphan"
    )


class WatchlistMember(Base):
    __tablename__ = "watchlist_members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    watchlist_id: Mapped[int] = mapped_column(ForeignKey("watchlists.id"))
    ticker_symbol: Mapped[str] = mapped_column(ForeignKey("tickers.symbol"))

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )

    watchlist: Mapped["Watchlist"] = relationship("Watchlist", back_populates="members")
    ticker: Mapped["Ticker"] = relationship("Ticker")


class DailyPrice(Base):
    __tablename__ = "daily_prices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ticker_symbol: Mapped[str] = mapped_column(ForeignKey("tickers.symbol"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)

    open: Mapped[float | None] = mapped_column(Numeric(18, 4), nullable=True)
    high: Mapped[float | None] = mapped_column(Numeric(18, 4), nullable=True)
    low: Mapped[float | None] = mapped_column(Numeric(18, 4), nullable=True)
    close: Mapped[float | None] = mapped_column(Numeric(18, 4), nullable=True)
    volume: Mapped[int | None] = mapped_column(Integer, nullable=True)
    adj_close: Mapped[float | None] = mapped_column(Numeric(18, 4), nullable=True)

    source: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )

    ticker: Mapped["Ticker"] = relationship("Ticker", back_populates="daily_prices")

    __table_args__ = (
        UniqueConstraint("ticker_symbol", "date", name="uq_daily_price_symbol_date"),
    )


class AnalysisSnapshot(Base):
    __tablename__ = "analysis_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ticker_symbol: Mapped[str] = mapped_column(ForeignKey("tickers.symbol"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)

    ma_20: Mapped[float | None] = mapped_column(Numeric(18, 4), nullable=True)
    ma_50: Mapped[float | None] = mapped_column(Numeric(18, 4), nullable=True)
    ma_200: Mapped[float | None] = mapped_column(Numeric(18, 4), nullable=True)
    rsi_14: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)

    above_20dma: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    above_50dma: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    above_200dma: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    rsi_zone: Mapped[str | None] = mapped_column(String, nullable=True)  # "oversold", etc.

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )

    ticker: Mapped["Ticker"] = relationship("Ticker", back_populates="analysis_snapshots")

    __table_args__ = (
        UniqueConstraint("ticker_symbol", "date", name="uq_analysis_symbol_date"),
    )


class NewsItem(Base):
    __tablename__ = "news_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ticker_symbol: Mapped[str | None] = mapped_column(ForeignKey("tickers.symbol"), index=True, nullable=True)

    source: Mapped[str | None] = mapped_column(String, nullable=True)
    headline: Mapped[str] = mapped_column(String, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    url: Mapped[str | None] = mapped_column(String, nullable=True)

    published_at: Mapped[datetime] = mapped_column(DateTime, index=True)

    sentiment_score: Mapped[float | None] = mapped_column(Numeric(8, 4), nullable=True)
    sentiment_label: Mapped[str | None] = mapped_column(String, nullable=True)

    raw_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )

    ticker: Mapped["Ticker"] = relationship("Ticker", back_populates="news_items")


class Brief(Base):
    __tablename__ = "briefs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)

    text: Mapped[str] = mapped_column(Text, nullable=False)
    audio_path: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )

    user: Mapped["User"] = relationship("User", back_populates="briefs")

    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_brief_user_date"),
    )
