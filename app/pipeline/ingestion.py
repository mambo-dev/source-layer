
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy import  select, update, func
from sqlalchemy.dialects.postgresql import insert
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

    pages = []

    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""

        if not text.strip():
            continue

        pages.append({
            "page": page_number,
            "text": text,
            "filename": filename
        })

    if not pages:
        raise ValueError(
            "PDF contains no extractable text"
        )

    return pages





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




    

def save_chunks_to_db(chunks, db, document_id):
    if not chunks:
         raise ValueError("no chunks provided")
    try:
 
        chunk_rows = [{
                        "document_id":document_id,
                        "page":chunk["page"],
                        "chunk_index":chunk["chunk_index"],
                        "text":chunk["text"]
        } for chunk in chunks ]

        stmt = insert(DocumentChunks).values(chunk_rows)

        stmt = stmt.on_conflict_do_nothing(
            constraint="uq_document_page_chunk"
        )


        db.execute(stmt)
        db.commit()

        return document_id
    except Exception as err:
        logger.error(f"Failed to save documents or chunks -> {err}")
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
        logger.error(f"Embedding failed: {err}")
        raise 




def verify_document_embeddings(db, document_id):
    total_chunks = db.scalar(
        select(func.count())
        .select_from(DocumentChunks)
        .where(DocumentChunks.document_id == document_id)
    )

    missing_embeddings = db.scalar(
        select(func.count())
        .select_from(DocumentChunks)
        .where(
            DocumentChunks.document_id == document_id,
            DocumentChunks.embedding.is_(None)
        )
    )

    if total_chunks == 0:
        raise ValueError(
            f"Document {document_id} has no chunks"
        )

    if missing_embeddings > 0:
        raise ValueError(
            f"Document {document_id} has "
            f"{missing_embeddings} chunks without embeddings"
        )

    return True


class EmbeddingServiceError(Exception):
    """An embedding operation failed and may be retried."""

@celery.task(bind=True, max_retries=3)
def start_document_processing(self, upload_dir, original_file_name, document_id):

    request_timer = time.perf_counter()

    with SessionLocal() as db:
        
        try:
            logger.info(f"Processing {original_file_name}")
            document_id = save_chunks_to_db(create_chunk_indexes(read_pdf(filename=str(upload_dir))),db, document_id)

            if document_id:
                stmt = (
                    update(Document).where(Document.id == document_id).values(status = "processing",filename=original_file_name, storage_path=str(upload_dir))
                )
                db.execute(stmt)
                db.commit()


            logger.info(f"Document chunks saved; generating embeddings {original_file_name}")
            stmt = (
                    update(Document).where(Document.id == document_id).values(status = "processing")
                )
            db.execute(stmt)
            db.commit()        

   

            try:
                update_db_chunks(db, document_id)
            except Exception as exc:
                raise EmbeddingServiceError(
                    f"Embedding operation failed for document {document_id}"
                ) from exc

            
            verify_document_embeddings(db, document_id=document_id)


            
            stmt = (
                    update(Document).where(Document.id == document_id).values(status = "completed")
                )
            db.execute(stmt)
            db.commit()

            logger.info(
                f"Completed ingestion: document_id={document_id}"
            )

        
        except Exception as exc:
            retryable = isinstance(exc, EmbeddingServiceError)
            retries_remaining = (
                self.request.retries < self.max_retries
            )

            if retryable and retries_remaining:
                logger.warning(
                    f"Retrying document {document_id}: {exc}"
                )

                raise self.retry(
                    exc=exc,
                    countdown=2 ** self.request.retries
                )                

                        
            stmt = (
                    select(Document).where(Document.id == document_id)
                )

            current_document = db.scalars(stmt).first()

            if current_document.status != "completed":
                stmt = (
                    update(Document).where(Document.id == document_id).values(status = "failed")
                )
                db.execute(stmt)
                db.commit()

            logger.error(f"Error: {exc}")
            raise Exception("Something went wrong")
        try:
            with SessionLocal() as db:
                db.execute(
                    update(Document)
                    .where(Document.id == document_id)
                    .values(status="failed")
                )
                db.commit()
        except Exception:
            logger.exception(
                f"Could not mark document {document_id} as failed"
            )

        logger.exception(
            f"Ingestion failed: document_id={document_id}"
        )

        raise

    try:
        duration = time.perf_counter() - start_time

        update_metric_file(
            "Document Upload and Processing - with celery background worker",
            round(duration, 2)
        )
    except Exception:
        logger.exception(
            "Failed to record ingestion metric"
        )

    return document_id

