from sqlalchemy import Column, Integer, String
from .database import Base

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String, unique=True, nullable=False)
    username = Column(String, unique=True, nullable=False)
    first_name = Column(String, nullable=False)
    second_name = Column(String,  nullable=False)
    password_hash = Column(String,  nullable=False)
