from sqlalchemy import create_engine
from settings import settings
from sqlalchemy.orm import sessionmaker, declarative_base


engine = create_engine(settings.database_url)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

base = declarative_base()