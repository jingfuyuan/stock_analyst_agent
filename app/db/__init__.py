from .session import Base
from .session import SessionLocal, Base

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()