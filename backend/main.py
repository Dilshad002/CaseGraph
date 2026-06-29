from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from ingestion.ocr import extract_text_from_image
from ingestion.cleaner import clean_text

app = FastAPI(title="CaseGraph API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    contents = await file.read()
    extracted_text = extract_text_from_image(contents)
    cleaned_text = clean_text(extracted_text)
    return {"filename": file.filename,
        "raw_text": extracted_text,
        "cleaned_text": cleaned_text}
