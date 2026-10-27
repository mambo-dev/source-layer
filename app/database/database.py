from sqlalchemy import create_engine
from app.settings import settings
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.engine import URL

database_url = URL.create(
    drivername="postgresql+psycopg",
    username=settings.db_username,
    password=settings.db_password,
    host=settings.db_host,
    port=settings.db_port,
    database=settings.db_name
)

engine = create_engine(database_url)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()

Base = declarative_base()

