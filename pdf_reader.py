import time
from agent_api import embed_text, get_answer
import numpy as np
from pypdf import PdfReader 
from sklearn.metrics.pairwise import cosine_similarity
from langchain_text_splitters import RecursiveCharacterTextSplitter
from database.database import SessionLocal 
from database.models import Document, DocumentChunks 
from sqlalchemy import insert, select, update

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



pdf = read_pdf('fictional_legal_case_file.pdf')


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

chunk_with_index = create_chunk_indexes(pdf)


    

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
    finally:
         db.close()

      



db = SessionLocal()

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
    
          
def retrieve_top_embeddings(question, db, document_id, top_k =3):
    embedded_question = embed_text(question)[0]
    distance = DocumentChunks.embedding.cosine_distance(embedded_question)
    query = (select(DocumentChunks,(1 - distance).label("similarity")).
              where(DocumentChunks.embedding.is_not(None),DocumentChunks.document_id == document_id).
              order_by(distance).limit(top_k)
            )

    similarities = db.execute(query).all()
    for sim in similarities:
        print(f"Page: {sim.DocumentChunks.page}, Chunk Index: {sim.DocumentChunks.chunk_index}, Similarity: {sim.similarity}")
    return similarities


def build_context(top_docs):
    
    prompt = (
                "You are a document analysis assistant. Answer the user's question using only the supplied context."
                "If the information is not available, say so."
                "Cite the document name and page number."
                "Do not invent facts.\n"
                "CONTEXT: \n\n"
                )
    result = []
    source_count = 1
    for chunk, similarity in top_docs:
        document_name = chunk.document.filename
        page = chunk.page
        result.append(f"Source {source_count} ,{document_name}, {page}")
        text = chunk.text
        result.append(text)
        source_count +=1

    return prompt + "\n\n".join(result)

     

# question = "What evidence did the claimant present to support their case?"

# start = time.perf_counter()
# results = retrieve_top_embeddings(question,db,7, top_k=3)
# print("Question embedding + retrieval:", round(time.perf_counter() - start, 2), "seconds")


# if __name__ == "__main__":
#     document_id = save_chunks_to_db(chunk_with_index)
#     print("Saved document:", document_id)
