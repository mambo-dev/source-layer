from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy import insert, select, update
from pypdf import PdfReader 
from app.database.models import Document, DocumentChunks 
from app.database.database import SessionLocal 
from app.llm.agent_api import embed_text
from app.core.workers import celery
from app.core.logger import logger
from metrics import update_metric_file
import time


splitter = RecursiveCharacterTextSplitter(
    chunk_size = 1000,
    chunk_overlap=150
)

def read_pdf(filename):
    reader = PdfReader(filename)

    extracted_pages_and_information = []
    for page in reader.pages:

            extracted_pages_and_information.append({
                  "page":page.page_number + 1,
                  "text":page.extract_text(),
                  "filename": filename
            })

    return extracted_pages_and_information






def create_chunk_indexes(pdf) ->  list:
    
    chunk_with_index = []
    for page in pdf:
        chunks = splitter.split_text(page["text"])
        for i, chunk in enumerate(chunks):
                indexed_chunks  = {
                    "page":page["page"],
                    "chunk_index":i,
                    "text":chunk,
                    "filename": page["filename"]
                }
                chunk_with_index.append(indexed_chunks)

    return chunk_with_index




    

def save_chunks_to_db(chunks, db):
    if not chunks:
         raise ValueError("no chunks provided")
    try:
        document = Document(filename=chunks[0]["filename"])
        db.add(document)
        db.flush()
        chunk_rows = [{
                        "document_id":document.id,
                        "page":chunk["page"],
                        "chunk_index":chunk["chunk_index"],
                        "text":chunk["text"]
        } for chunk in chunks ]

        db.execute(insert(DocumentChunks), chunk_rows)
        db.commit()

        return document.id
    except Exception as err:
        print(f"Failed to save documents or chunks -> {err}")
        db.rollback()
        raise 


      




def update_db_chunks(db,document_id):
    batch_size = 10
    try:
        while True:
            statement = (select(DocumentChunks).
                         where(DocumentChunks.embedding.is_(None),DocumentChunks.document_id == document_id).
                         order_by(DocumentChunks.id).
                         limit(batch_size))
            
            batch =  db.scalars(statement).all()

            if not batch:
                break

            texts = [chunk.text for chunk in batch]
            embeddings = embed_text(text=texts)
            bulk_updates = []

            if len(embeddings) != len(batch):
                raise ValueError("Embedding count mismatch")
            
            for chunk, embedding in zip(batch, embeddings):
                if len(embedding) != 768:
                    raise ValueError(
                        f"Invalid embedding dimension for chunk {chunk.id}"
                    )

                updates = {
                    'id':chunk.id,
                    'embedding':embedding
                }
                
                bulk_updates.append(updates)


            
            db.execute(update(DocumentChunks),bulk_updates)

            db.commit()
            
        return True
    except Exception as err:
        db.rollback()
        print(f"Embedding failed: {err}")
        raise 



@celery.task(bind=True, retries=3)
def start_document_processing(self, upload_dir, original_file_name):
    db = SessionLocal()
    request_timer = time.perf_counter()
    try:
        logger.info(f"Processing {original_file_name}")
        document_id = save_chunks_to_db(create_chunk_indexes(read_pdf(filename=str(upload_dir))),db)

        if document_id:
            stmt = (
                update(Document).where(Document.id == document_id).values(status = "pending",filename=original_file_name, storage_path=str(upload_dir))
            )
            db.execute(stmt)
            db.commit()

    except Exception as exc:
         logger.error(f"Error: {exc}, retrying...")
         raise self.retry(exc=exc, countdown= 2 ** self.request.retries)

    
    try:
        logger.info(f"Document chunked and saved embeddings {original_file_name} updating embeddings to chunks")
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

        update_metric_file("Document Upload and Processing - with celery background worker", round(time.perf_counter() - request_timer, 2))
        return document_id
    
    except Exception as exc:
        stmt = (
            update(Document).where(Document.id == document_id).values(status = "failed")
        )
        db.execute(stmt)
        db.commit()
        logger.error(f"Error: {exc}, retrying...")
        raise self.retry(exc=exc, countdown= 2 ** self.request.retries)
    
    finally:
         db.close()
