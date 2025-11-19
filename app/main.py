from app.db.session import Base, engine
# from app.db import models
from app.db.session import SessionLocal
from app.db.models import User, Watchlist, WatchlistMember, Ticker

def init_db():
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    init_db()
    with SessionLocal() as session:
        user = User(
            id=2,
            email="jingfuyuan@x.com",
            name="Fuyuan Jing",
            tts_enabled=False
        )
        session.add(user)
        session.commit()
