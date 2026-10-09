from fastapi import FastAPI,Depends,HTTPException
from fastapi import status
from schemas import Response, UserResponse, RegisterBody, LoginBody, RegisterResponse
from auth import hash_password, verify_password
from database.models import User
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from database.database import engine, SessionLocal, Base

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()
    


app = FastAPI()


@app.post("/auth/login", status_code=status.HTTP_200_OK, response_model=Response[UserResponse])
def login(login_body:LoginBody):
    is_valid = verify_password(login_body.password, "sdfsdf")
    return {
        "success":True,
        "message":"Successfully logged in our user",
        "data":{
            "access_token":"logged-in-user"
        }
    }

@app.post("/auth/register", status_code=status.HTTP_201_CREATED, response_model=Response[RegisterResponse])
def register(body: RegisterBody, db:Session = Depends(get_db)):

    existing_email = (
        db.query(User).filter(User.email == body.email).first() 
    )

    existing_username = (
        db.query(User).filter(User.username == body.username).first()
        )

    if existing_email :
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="email already registered"
        )
    
    if existing_username :
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="username already exists"
        )


    

    hashed_password = hash_password(body.password)

   
    db_user = User(first_name=body.first_name,
                   second_name = body.second_name,
                   username = body.username,
                   email = body.email,
                   password_hash = hashed_password
                   )


    try:
        db.add(db_user)

        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email or username already registered"
        )
    
    db.refresh(db_user)
 
    return {
        "success":True,
        "message":"Account has been successfully created",
        "data":{
            "id":db_user.id
        }
    }


@app.get("/auth/me", status_code=status.HTTP_200_OK, response_model=Response[UserResponse])
def get_profile():
    return {
        "success":True,
        "message":"Successfully logged in our user",
        "data":{}
    }