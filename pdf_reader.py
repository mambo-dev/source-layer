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


    

def save_chunks_to_db(chunks):
    if not chunks:
         raise ValueError("no chunks provided")
    db = SessionLocal()
    print("we have a db session")
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

      
      
save_chunks_to_db(chunk_with_index)




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
            

    except Exception as err:
        db.rollback()
        print(f"Embedding failed: {err}")
        raise
    
          

     
     


def retreive_chunks(question, top_k =3):
    embed_question = embed_text(question)[0]
    embedded_chunks = []
    similarities = []
    for chunk in embedded_chunks:
        scores = cosine_similarity(X=np.array(embed_question).reshape(1,-1), Y=np.array(chunk["embedding"]).reshape(1,-1))[0]
        similarities.append({
            "chunk":chunk,
            "score":scores.tolist()[0]
        })

    similarities.sort(reverse=True, key= lambda x:x["score"])
 
    return similarities[:top_k]


# if __name__ == "__main__":
#     document_id = save_chunks_to_db(chunk_with_index)
#     print("Saved document:", document_id)

# def chunk_by_text_page(pdf_pages):
#     chunks = []

#     id = 0
#     current_heading = None
#     current_lines = []
    
#     current_pages = []
#     for page in pdf_pages:
#         lines = page["text"].split("\n")


#         for line in lines:
#             line = line.strip()
            
#             if line and line.isupper():
                
#                 if current_heading is not None and current_lines and any(line.strip() for line in current_lines):
#                     id += 1
#                     chunks.append({
#                         "id":id,
#                         "document":page["filename"],
#                         "page": current_pages,
#                         "heading":current_heading,
#                         "text":"\n".join(current_lines),

#                     })
#                 current_lines  = []
#                 current_pages = []
#                 current_heading = line
      
                
#             elif current_heading is not None:
#                 current_lines.append(line)
#                 if page["page"] not in current_pages:
#                     current_pages.append(page["page"])


#     if current_heading is not None and current_lines and any(line.strip() for line in current_lines):
#         id += 1
#         chunks.append({
#             "id": id,
#             "document": page["filename"],
#             "page":current_pages,
#             "heading": current_heading,
#             "text": "\n".join(current_lines)
#         })
        
#     return chunks
            

# sections = chunk_by_text_page(pdf)


# # for chunk in chunks:
# #     print("ID:", chunk["id"])
# #     print("Heading:", chunk["heading"])
# #     print("Pages:", chunk["page"])
# #     print("Text length:", len(chunk["text"]))
# #     print("-" * 40)



# def split_text(text, chunk_size = 4, overlap = 1):
#     if overlap >= chunk_size:
#         raise Exception("over lap should be less than chunk size")
    
#     text = text.split()
#     start = 0
#     end = start + chunk_size
#     chunks = []
#     while start < len(text):
#         chunks.append(" ".join(text[start:end]))
#         if end >= len(text):
#             break
#         start += chunk_size - overlap
#         end = start + chunk_size


#     return chunks

# def split_sections(sections, chunk_size = 400, overlap = 50):

#     chunked_sections = []
#     id = 0
#     for section in sections:
#         chunked_texts = split_text(section["text"], chunk_size=chunk_size, overlap=overlap)

#         for ct in chunked_texts:
#             id += 1
#             chunked_section_dictionary = {
#                 "id":id,
#                 "section_id":section["id"],
#                 "document":section["document"],
#                 "page":section["page"],
#                 "heading":section["heading"],
#                 "text":ct

#             }

#             chunked_sections.append(chunked_section_dictionary)

#     return chunked_sections



# chunks = split_sections(sections=sections)



# def embed_chunks(chunks, batch_size = 10):
#     embedded_chunks = []
#     for i in range(0, len(chunks), batch_size):
#         batch = chunks[i:i + batch_size]
#         texts = [f"{chunk['heading']}\n{chunk['text']}" for chunk in batch]
#         embeddings = embed_text(texts)
#         if len(batch) != len(embeddings):
#              raise ValueError("Embedding count does not match chunk count")
        
#         for chunk, vectors in zip(batch, embeddings):
#             chunk['embedding'] = vectors
#             embedded_chunks.append(chunk)
#     return embedded_chunks

# def retreive_chunks(question, embedded_chunks, top_k =3):
#     embed_question = embed_text(question)[0]
    
#     similarities = []
#     for chunk in embedded_chunks:
#         scores = cosine_similarity(X=np.array(embed_question).reshape(1,-1), Y=np.array(chunk["embedding"]).reshape(1,-1))[0]
#         similarities.append({
#             "chunk":chunk,
#             "score":scores.tolist()[0]
#         })

#     similarities.sort(reverse=True, key= lambda x:x["score"])
 
#     return similarities[:top_k]


# question = "What evidence did the claimant present to support their case?"

# start = time.perf_counter()
# embedded_chunks = embed_chunks(chunks)
# print("Document embedding:", round(time.perf_counter() - start, 2), "seconds")

# start = time.perf_counter()
# results = retreive_chunks(question, embedded_chunks, top_k=3)
# print("Question embedding + retrieval:", round(time.perf_counter() - start, 2), "seconds")





# def build_context_from_chunks(retrieved_chunks, question):
#     result = ("You are a legal document assistant.\nAnswer the question using only the provided context.\nIf the answer is not in the context, say you cannot find it.\nCite the section headings and page numbers and Do not omit relevant exhibits or facts. \n\n CONTEXT:\n")
#     document_info = []

#     for chunks in retrieved_chunks:
#         chunk = chunks["chunk"]
#         page_numbers = []
#         [page_numbers.append(str(pn)) for pn in chunk['page']]
#         heading_page = f"[{chunk['heading']}, page{"'s" if len(page_numbers) >1 else ""} {",".join(page_numbers)}]"
#         document_info.append(heading_page)
#         document_info.append(chunk['text'])
    
#     document_info.append('QUESTION:')
#     document_info.append(question)
#     result += "\n\n".join(document_info)
#     return result




# def generate_answer(question,retrieved_chunks):
#     prompt = build_context_from_chunks(retrieved_chunks, question)

#     response = get_answer(prompt)
#     print(response)
#     return response



# start = time.perf_counter()
# answer = generate_answer(question, results)
# print("Generation:", round(time.perf_counter() - start, 2), "seconds")
