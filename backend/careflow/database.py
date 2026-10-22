from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from .config import get_settings


class Base(DeclarativeBase):
    pass


url = get_settings().database_url
engine = create_engine(url, connect_args={"check_same_thread": False} if url.startswith("sqlite") else {}, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def session_scope():
    with SessionLocal() as session:
        yield session
