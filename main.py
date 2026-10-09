from fastapi import FastAPI
from fastapi import status
from schemas import Response, UserResponse, RegisterBody, LoginBody
from auth import hash_password, verify_password
    


app = FastAPI()


@app.post("/auth/login", status_code=status.HTTP_202_ACCEPTED, response_model=Response[UserResponse])
def login(login_body:LoginBody):
    is_valid = verify_password(login_body.password, "sdfsdf")
    return {
        "success":True,
        "message":"Successfully logged in our user",
        "data":{
            "access_token":"logged-in-user"
        }
    }

@app.post("/auth/register", status_code=status.HTTP_201_CREATED, response_model=Response[UserResponse])
def register(register_body: RegisterBody):
    hashed_password = hash_password(register_body.password)
    print(hashed_password)
    return {
        "success":True,
        "message":"Successfully logged in our user",
        "data":{
            "first_name":register_body.first_name,
            "second_name":register_body.second_name,
            "username":register_body.username,
            "email":register_body.email
        }
    }


@app.get("/auth/me", status_code=status.HTTP_200_OK, response_model=Response[UserResponse])
def get_profile():
    return {
        "success":True,
        "message":"Successfully logged in our user",
        "data":{}
    }