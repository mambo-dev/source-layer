from fastapi import FastAPI,Depends,HTTPException, UploadFile, File
from fastapi import status
from requests import get
from schemas import Response, UserResponse, RegisterBody, LoginResponse, RegisterResponse,TokenData,DocumentUploadResponse, QuestionResponse,QuestionBody
from auth import hash_password, verify_password
from database.models import User, Document, DocumentChunks
from sqlalchemy import update
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from database.database import engine, SessionLocal, Base
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from typing import Annotated
from datetime import timedelta, datetime, timezone
import jwt
from jwt.exceptions import InvalidTokenError
from settings import settings
from pathlib import Path
import shutil
from pdf_reader import read_pdf, create_chunk_indexes, save_chunks_to_db, update_db_chunks, retrieve_hybrid_chunks, build_context
from uuid import uuid4
import time
from metrics import update_metric_file
from agent_api import get_answer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

Base.metadata.create_all(bind=engine)




def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()
    


app = FastAPI()




def get_user(db, username):
    user = db.query(User).filter(User.username == username).first()

    return user

def create_access_token(data:dict, expires_delta:timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expires = datetime.now(timezone.utc) + expires_delta
    else:
        expires = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp":expires})
    encoded_jwt = jwt.encode(to_encode, key=settings.jwt_secret , algorithm=settings.algorithm)

    return encoded_jwt


def authenticate_user(db, username, password):
    user = get_user(db, username)

    if not user:
        return False
    if not verify_password(password, hashed_password=user.password_hash):
        return False
    return user


def get_current_user(token:Annotated[str, Depends(oauth2_scheme)], db:Session = Depends(get_db)):
        credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

        try:
            payload = jwt.decode(token, key=settings.jwt_secret, algorithms=[settings.algorithm])
            username = payload.get("sub")

            if username is None:
            
                raise credentials_exception
            token_data = TokenData(username=username)
        except InvalidTokenError as err:
            print(f"Token decode error: {err}")
            raise credentials_exception
    
        user = get_user(db, token_data.username)

        if not user:
        
            raise credentials_exception

        return user
        


@app.post("/auth/login", status_code=status.HTTP_200_OK, response_model=Response[LoginResponse])
def login(formData:Annotated[OAuth2PasswordRequestForm, Depends()], db:Session = Depends(get_db)):
    
    user = authenticate_user(db, formData.username, formData.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )

    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)

    access_token = create_access_token({"sub":user.username}, access_token_expires)

    return {
        "success":True,
        "message":"Successfully logged in our user",
        "data":{
            "access_token":access_token,
            "token_type":"Bearer"
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
def get_profile(current_user: Annotated[User, Depends(get_current_user)]):
    return {
        "success":True,
        "message":"Successfully retrieved user profile",
        "data":{
            "first_name":current_user.first_name,
            "second_name":current_user.second_name,
            "username":current_user.username,
            "email":current_user.email
        }
    }




@app.post("/documents/upload", status_code=status.HTTP_200_OK, response_model=Response[DocumentUploadResponse])
def upload_document(user:Annotated[User,Depends(get_current_user)],db:Session = Depends(get_db), 
                    file:UploadFile = File(...)):

    request_timer = time.perf_counter()
    if file.content_type != 'application/pdf':
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="only pdf files allowed")
   
    stored_file_name = f"{uuid4().hex}.pdf"
    upload_dir = Path("uploads") / str(user.id)
    upload_dir = upload_dir / stored_file_name
    upload_dir.parent.mkdir(parents=True, exist_ok=True)
    original_file_name = file.filename
   

    try:
        with upload_dir.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    finally:
        file.file.close()

    try:
        document_id = save_chunks_to_db(create_chunk_indexes(read_pdf(filename=str(upload_dir))),db)
        if document_id:
            stmt = (
                update(Document).where(Document.id == document_id).values(status = "pending",filename=original_file_name, storage_path=str(upload_dir))
            )
            db.execute(stmt)
            db.commit()
        

    except Exception as err:
        print(f"Processing failed: {str(err)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="processing failed please try again")


    try:

        stmt = (
                update(Document).where(Document.id == document_id).values(status = "processing")
            )
        db.execute(stmt)
        db.commit()        

        update_db_chunks(db, document_id)
        stmt = (
                update(Document).where(Document.id == document_id).values(status = "completed")
            )
        db.execute(stmt)
        db.commit()
        update_metric_file("Document Upload and Processing -MVP", round(time.perf_counter() - request_timer, 2))
        return {
            "success":True,
            "message": "Document uploaded and processed successfully",
            "data":{
                "document_id":document_id
            }
        }

    except Exception as err:
            stmt = (
                update(Document).where(Document.id == document_id).values(status = "failed")
            )
            db.execute(stmt)
            db.commit()
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="document processing failed")



@app.post('/ai/ask/{document_id}', status_code=status.HTTP_200_OK, response_model = Response[QuestionResponse])
def ask_question( body:QuestionBody,document_id:int, user:Annotated[User,Depends(get_current_user)], db:Session = Depends(get_db)):
    request_timer = time.perf_counter()

    try:
        top_chunks = retrieve_hybrid_chunks(body.question,document_id, db)

        prompt = build_context(top_chunks, body.question)
        
        answer = get_answer(prompt)


        update_metric_file(metric_name="Answer retrieval - MVP",metric_perf=round(time.perf_counter()-request_timer, 2))

        return {
            "success":True,
            "message": "Document uploaded and processed successfully",
            "data":{
                "response":answer,
                "sources":[f"Source {i+1}: {doc.DocumentChunks.document.filename}, Page: {doc.DocumentChunks.page}" for i, doc in enumerate(top_chunks)]
            }
        }
   
    except Exception as err:
        print(err)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve user resposne")
