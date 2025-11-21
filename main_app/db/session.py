from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from main_app.core.config import settings

engine = create_engine(settings.DATABASE_URL)
SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()