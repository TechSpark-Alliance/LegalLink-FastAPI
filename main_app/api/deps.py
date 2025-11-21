from fastapi import Depends
from sqlalchemy.orm import Session
from main_app.db.session import get_db


def get_db_session() -> Session:
    """Dependency to get database session"""
    return next(get_db())