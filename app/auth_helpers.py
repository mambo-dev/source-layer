from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

from app.settings import settings

password_hash = PasswordHash.recommended()

def hash_password(password:str):


    return password_hash.hash(password=password)

def verify_password(password, hashed_password):
    return password_hash.verify(password=password, hash=hashed_password)

def create_access_token(data:dict, expires_delta:timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expires = datetime.now(timezone.utc) + expires_delta
    else:
        expires = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp":expires})
    encoded_jwt = jwt.encode(to_encode, key=settings.jwt_secret , algorithm=settings.algorithm)

    return encoded_jwt
