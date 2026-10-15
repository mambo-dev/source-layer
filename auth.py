from pwdlib import PasswordHash

password_hash = PasswordHash.recommended()

def hash_password(password:str):


    return password_hash.hash(password=password)

def verify_password(password, hashed_password):
    return password_hash.verify(password=password, hash=hashed_password)

