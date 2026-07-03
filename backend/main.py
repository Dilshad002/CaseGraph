import uuid
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from backend.ingestion.ocr import extract_text_from_image
from backend.ingestion.cleaner import clean_text
from backend.ingestion.pdf_extractor import extract_text_from_pdf
from backend.nlp.ner import extract_entities
from backend.nlp.regex_extractor import extract_regex_entities, strip_overlapping_ner_entities
from backend.graph.writer import write_extractions_to_graph
from backend.nlp.field_stripper import strip_field_labels
from backend.reasoning.relation_extractor import extract_relationships

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

@app.post("/extract")
async def extract(file: UploadFile = File(...)):
    contents = await file.read()

    if file.filename.endswith(".pdf"):
        extracted_text = extract_text_from_pdf(contents)
    else:
        extracted_text = extract_text_from_image(contents)

    cleaned_text = clean_text(extracted_text)
    regex_entities = extract_regex_entities(cleaned_text) #original text

    ner_input = strip_field_labels(cleaned_text)  #strip field labels from cleaned text before NER
    entities = extract_entities(ner_input) 
    entities = strip_overlapping_ner_entities(entities, regex_entities)

    entity_texts = [e["text"] for e in entities] + \
        regex_entities.get("phone_numbers", []) + \
        regex_entities.get("vehicle_numbers", [])
    
    relationships = extract_relationships(cleaned_text, entity_texts)

    case_id = str(uuid.uuid4())
    write_extractions_to_graph(case_id, file.filename, entities, regex_entities)
    # write_relationships_to_graph(case_id, relationships, regex_entities.get("fir_number"))

    return {"filename": file.filename,
        "cleaned_text": cleaned_text,
        "entities": entities,
        "regex_entities": regex_entities,
        "relationships": relationships,
        }