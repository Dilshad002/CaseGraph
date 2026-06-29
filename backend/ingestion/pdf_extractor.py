import fitz

def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    text = ""
    with fitz.open(stream=pdf_bytes, filetype="pdf") as pdf_document:
        for page in pdf_document:
            text += page.get_text()
    return text.strip()
