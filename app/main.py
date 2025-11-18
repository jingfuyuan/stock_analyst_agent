from app.db.session import Base, engine
# from app.db import models
# from app.db.session import SessionLocal

def init_db():
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    init_db()
