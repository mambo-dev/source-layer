from sqlalchemy import Column, Integer, String
from .database import base

class User(base):
    tablename = 'users'

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False)
    username = Column(String, unique=True, nullable=False)
    first_name = Column(String, nullable=False)
    second_name = Column(String,  nullable=False)
    password = Column(String,  nullable=False)
