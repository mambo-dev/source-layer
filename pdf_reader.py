from embed import embed_text

from pypdf import PdfReader 

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

for chunk in chunks:
    print(embed_text(chunk['text']))