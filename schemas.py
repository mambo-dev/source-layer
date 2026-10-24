
from pydantic import BaseModel, EmailStr, Field, model_validator, field_validator
from typing import TypeVar, Generic
import re

T = TypeVar("T")


class LoginBody(BaseModel):
    username:str = Field(..., min_length=3, max_length=20 )
    password:str = Field(..., min_length=8)

class QuestionBody(BaseModel):
    question:str = Field(..., min_length=10)

class RegisterBody(BaseModel):
    username:str =  Field(..., min_length=3, max_length=20)
    email:EmailStr
    first_name:str =  Field(...,min_length=3, max_length=50)
    second_name:str =  Field(...,min_length=3, max_length=50)
    password:str
    confirm_password:str = Field(..., min_length=8)

    @field_validator("password")
    @classmethod
    def verify_password_strength(cls, value):
        if len(value) < 8:
            raise ValueError("password must be greater than 8 characters")
        
        if not any(char.isdigit() for char in value):
            raise ValueError("password must contain a number")
        
        if not any(char.isupper() for char in value):
            raise ValueError("password must contain an upper case")
        r"[\*\#\$\%\&\(\)\!]"
        if not re.search(r"[\*\#\$\%\&\(\)\!]", value) :
            raise ValueError("password must contain atleast one of '*#$%&()'")
        
        return value

    @model_validator(mode="after")
    def verify_passwords_match(self):
        if self.password != self.confirm_password:
            raise ValueError("passwords do not match")
        return self




class AuthResponse(BaseModel):
    access_token:str
    refresh_token:str


class UserResponse(BaseModel):
    first_name:str
    second_name:str
    username:str
    email:str

class LoginResponse(BaseModel):
    access_token:str
    token_type:str

class RegisterResponse(BaseModel):
    id:int

    
class Response(BaseModel, Generic[T]):
    success: bool = False
    message: str
    data: T

class TokenData(BaseModel):
    username: str | None = None

class DocumentUploadResponse(BaseModel):
    document_id:int

class QuestionResponse(BaseModel):
    response:str
    sources:list[str]