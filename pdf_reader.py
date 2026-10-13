from embed import embed_text
import numpy as np
from pypdf import PdfReader 
from sklearn.metrics.pairwise import cosine_similarity

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

def chunk_by_text_page(pdf_pages):
    chunks = []

    id = 0
    current_heading = None
    current_lines = []
    
    current_pages = []
    for page in pdf_pages:
        lines = page["text"].split("\n")


        for line in lines:
            line = line.strip()
            
            if line and line.isupper():
                
                if current_heading is not None and current_lines and any(line.strip() for line in current_lines):
                    id += 1
                    chunks.append({
                        "id":id,
                        "document":page["filename"],
                        "page": current_pages,
                        "heading":current_heading,
                        "text":"\n".join(current_lines),

                    })
                current_lines  = []
                current_pages = []
                current_heading = line
      
                
            elif current_heading is not None:
                current_lines.append(line)
                if page["page"] not in current_pages:
                    current_pages.append(page["page"])


    if current_heading is not None and current_lines and any(line.strip() for line in current_lines):
        id += 1
        chunks.append({
            "id": id,
            "document": page["filename"],
            "page":current_pages,
            "heading": current_heading,
            "text": "\n".join(current_lines)
        })
        
    return chunks
            

sections = chunk_by_text_page(pdf)


# for chunk in chunks:
#     print("ID:", chunk["id"])
#     print("Heading:", chunk["heading"])
#     print("Pages:", chunk["page"])
#     print("Text length:", len(chunk["text"]))
#     print("-" * 40)



def split_text(text, chunk_size = 4, overlap = 1):
    if overlap >= chunk_size:
        raise Exception("over lap should be less than chunk size")
    
    text = text.split()
    start = 0
    end = start + chunk_size
    chunks = []
    while start < len(text):
        chunks.append(" ".join(text[start:end]))
        if end >= len(text):
            break
        start += chunk_size - overlap
        end = start + chunk_size


    return chunks

def split_sections(sections, chunk_size = 400, overlap = 50):

    chunked_sections = []
    id = 0
    for section in sections:
        chunked_texts = split_text(section["text"], chunk_size=chunk_size, overlap=overlap)

        for ct in chunked_texts:
            id += 1
            chunked_section_dictionary = {
                "id":id,
                "section_id":section["id"],
                "document":section["document"],
                "page":section["page"],
                "heading":section["heading"],
                "text":ct

            }

            chunked_sections.append(chunked_section_dictionary)

    return chunked_sections



chunks = split_sections(sections=sections)



def embed_chunks(chunks, batch_size = 10):
    embedded_chunks = []
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        texts = [f"{chunk['heading']}\n{chunk['text']}" for chunk in batch]
        embeddings = embed_text(texts)
        if len(batch) != len(embeddings):
             raise ValueError("Embedding count does not match chunk count")
        
        for chunk, vectors in zip(batch, embeddings):
            chunk['embedding'] = vectors
            embedded_chunks.append(chunk)
    return embedded_chunks

def retreive_chunks(question, embedded_chunks, top_k =3):
    embed_question = embed_text(question)[0]
    
    similarities = []
    for chunk in embedded_chunks:
        scores = cosine_similarity(X=np.array(embed_question).reshape(1,-1), Y=np.array(chunk["embedding"]).reshape(1,-1))[0]
        similarities.append({
            "chunk":chunk,
            "score":scores.tolist()[0]
        })

    similarities.sort(reverse=True, key= lambda x:x["score"])
 
    return similarities[:top_k]


results = retreive_chunks("What evidence did the claimant present to support their case?",embed_chunks(chunks))

for result in results:
    print("Heading:", result["chunk"]["heading"])
    print("Pages:", result["chunk"]["page"])
    print("Similarity:", round(result["score"], 4))
    print("Text:", result["chunk"]["text"][:300])
    print("-" * 50)
