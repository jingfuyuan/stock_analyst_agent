from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# For MVP: SQLite file. Replace with Postgres URL later if needed
DATABASE_URL = "sqlite:///./personal_stock_analyst.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}, #needed only for SQLite + threads
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

class Base(DeclarativeBase):
    pass


