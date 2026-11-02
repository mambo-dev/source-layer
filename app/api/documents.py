from fastapi import Depends, HTTPException,  UploadFile, File,Request,APIRouter,status
from pathlib import Path
from typing import Annotated
from uuid_utils import uuid4
from app.api.auth import get_current_user
from app.database.database import get_db
from fastapi import HTTPException,status,Request
import time
from app.schemas import DocumentUploadResponse, Response
from app.database.models import  User
from sqlalchemy.orm import Session
import shutil
from app.core.logger import logger
from app.core.limiter import limiter
from app.pipeline.ingestion import start_document_processing
from app.core.workers import celery
from app.database.models import Document

router = APIRouter()

@router.post("/documents/upload", status_code=status.HTTP_200_OK, response_model=Response[DocumentUploadResponse])
@limiter.limit('5/minute')
def upload_document(request:Request,user:Annotated[User,Depends(get_current_user)],db:Session = Depends(get_db), 
                    file:UploadFile = File(...)):

    
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

        document = Document(filename= original_file_name, storage_path = str(upload_dir),status="queued")
        db.add(document)
        db.commit()
        db.refresh(document)


        task = start_document_processing.delay(str(upload_dir),original_file_name, document_id= document.id)
        return {
            "success":True,
            "message": "Document saved and queued for processing",
            "data":{
                "task_id":task.id
            }
        }

    except Exception as err:
            logger.error(f"Error: {err}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="document processing failed")


@router.get("/status/{task_id}")
@limiter.limit('5/minute')
async def get_status(request:Request,task_id: str, user:Annotated[User,Depends(get_current_user)]):
    result = celery.AsyncResult(task_id)
    print(result)
    return {
        "task_id": task_id,
        "status": result.status,
        "document_id": result.result if result.successful() else None,
    }