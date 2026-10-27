import time
from typing import Annotated
from app.core.limiter import limiter
from sqlalchemy.orm import Session
from app.api.auth import get_current_user
from app.database.database import get_db
from fastapi import Depends, HTTPException, Request,status, APIRouter
from app.schemas import QuestionBody, QuestionResponse, Response
from app.database.models import User
from metrics import update_metric_file
from app.pdf_reader import build_context, retrieve_hybrid_chunks
from app.agent_api import get_answer

router  = APIRouter()

@router.post('/ai/ask/{document_id}', status_code=status.HTTP_200_OK, response_model = Response[QuestionResponse])
@limiter.limit('5/minute')
def ask_question( request:Request,body:QuestionBody,document_id:int, user:Annotated[User,Depends(get_current_user)], db:Session = Depends(get_db)):
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
                "sources":[f"{chunk['chunk'].document.filename}, Page: {chunk['chunk'].page}" for _, chunk in top_chunks.items()]
            }
        }
   
    except Exception as err:
        print(err)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve user resposne")
