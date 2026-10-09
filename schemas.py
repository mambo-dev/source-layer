
from pydantic import BaseModel, EmailStr, Field, model_validator, field_validator
from typing import TypeVar, Generic
import re

T = TypeVar("T")


class LoginBody(BaseModel):
    username:str
    password:str

class RegisterBody(BaseModel):
    username:str =  Field(..., min_length=3, max_length=20)
    email:EmailStr
    first_name:str =  Field(...,min_length=3, max_length=50)
    second_name:str =  Field(...,min_length=3, max_length=50)
    
    confirm_password:str = Field(..., min_length=8)
    @field_validator("password")
    @classmethod
    def verify_password_strength(self):
        if len(self.password) > 8:
            raise ValueError("password must be greather than 8 characters")
        elif not any(char.isdigit() for char in self.password ):
            raise ValueError("password must contain a number")
        elif not any(char.isupper() for char in self.password):
            raise ValueError("password must contain an upper case")
        elif re.search("[* #$%&()]", self.password):
            raise ValueError("password must contain atleast one of '[* #$%&()]'")


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


    
class Response(BaseModel, Generic[T]):
    success: bool = False
    message: str
    data: T