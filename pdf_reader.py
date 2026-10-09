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
    for page in pdf_pages:
        lines = page["text"].split("\n")


        current_pages = []
        for line in lines:
            line = line.strip()
            
            if line and line.isupper():
                
                if current_heading is not None and current_lines and any(line.strip() for line in current_lines):

                    if page["page"] not in current_pages:
                        current_pages.append(page["page"])

                    id += 1
                    chunks.append({
                        "id":id,
                        "document":page["filename"],
                        "page": current_pages,
                        "heading":current_heading,
                        "text":"\n".join(current_lines),

                    })
                current_lines  = []
                current_heading = line
      
                
            elif current_heading is not None:
                current_lines.append(line)

          
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
            

chunks = chunk_by_text_page(pdf)

for chunk in chunks:
    print(
        chunk["id"],
        chunk["page"],
        chunk["heading"],
        len(chunk["text"].strip())
    )



