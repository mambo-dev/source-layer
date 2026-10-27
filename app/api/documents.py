from fastapi import Depends, HTTPException,  UploadFile, File,Request,APIRouter,status
from pathlib import Path
from typing import Annotated
from sqlalchemy import update
from uuid_utils import uuid4
from app.api.auth import get_current_user
from app.database.database import get_db
from fastapi import HTTPException,status,Request
import time
from app.schemas import DocumentUploadResponse, Response
from app.database.models import Document, User
from sqlalchemy.orm import Session
import shutil
from metrics import update_metric_file
from app.pdf_reader import read_pdf, create_chunk_indexes, save_chunks_to_db, update_db_chunks
from app.core.limiter import limiter
router = APIRouter()

@router.post("/documents/upload", status_code=status.HTTP_200_OK, response_model=Response[DocumentUploadResponse])
@limiter.limit('5/minute')
def upload_document(request:Request,user:Annotated[User,Depends(get_current_user)],db:Session = Depends(get_db), 
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


