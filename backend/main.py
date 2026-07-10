import uuid
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from backend.ingestion.ocr import extract_text_from_image
from backend.ingestion.cleaner import clean_text
from backend.ingestion.pdf_extractor import extract_text_from_pdf
from backend.nlp.ner import extract_entities
from backend.nlp.regex_extractor import extract_regex_entities, strip_overlapping_ner_entities, extract_person_attributes, extract_incident_details
from backend.graph.writer import write_extractions_to_graph, write_relationships_to_graph, write_person_attributes, write_incident_to_graph
from backend.nlp.field_stripper import strip_field_labels
from backend.reasoning.relation_extractor import extract_relationships, build_role_map
from backend.reasoning.contradiction_detection import detect_contradictions
from backend.assistant.query_engine import query as run_query
from backend.graph.connection import get_session

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
    write_relationships_to_graph(case_id, relationships, file.filename, entities, regex_entities.get("fir_number"))

    role_map = build_role_map(cleaned_text)
    person_attrs = extract_person_attributes(cleaned_text, role_map)
    fir_number = regex_entities.get("fir_number")

    for p in person_attrs:
        write_person_attributes(p["name"], p["attributes"], fir_number, file.filename)

    incident = extract_incident_details(cleaned_text)
    accused_name = None
    for name, data in role_map.items():
        if "accused" in data.get("unambiguous", set()):
            accused_name = name
            break

    write_incident_to_graph(fir_number, incident, accused_name)

    return {"filename": file.filename,
        "cleaned_text": cleaned_text,
        "entities": entities,
        "regex_entities": regex_entities,
        "relationships": relationships,
        }

@app.get("/graph")
def get_graph():
    with get_session() as session:
        nodes = {}
        edges = []

        # Case nodes
        result = session.run("""
        MATCH (c:Case)-[:MENTIONS]->(e:Entity)
        WHERE e.type IN ['person', 'location', 'organization', 'vehicle_number', 'phone_number', 'facility', 'time', 'date']
        RETURN DISTINCT e.text AS id, e.type AS type, c.fir_number AS fir
        """)
        for r in result:
            nodes[r["id"]] = {"id": r["id"], "label": f"FIR {r['id']}", "type": "Case"}

        # Entity nodes via MENTIONS
        result = session.run("""
            MATCH (c:Case)-[:MENTIONS]->(e:Entity)
            RETURN DISTINCT e.text AS id, e.type AS type, c.fir_number AS fir
        """)
        for r in result:
            if r["id"] not in nodes:
                label = r["id"][:20] + "..." if len(r["id"]) > 20 else r["id"]
                nodes[r["id"]] = {"id": r["id"], "label": label, "type": r["type"]}
            edges.append({"source": r["fir"], "target": r["id"], "label": "MENTIONS", "type": "MENTIONS"})

        # RELATION edges
        result = session.run("""
            MATCH (s:Entity)-[r:RELATION]->(o:Entity)
            RETURN s.text AS source, o.text AS target, r.type AS type
        """)
        for r in result:
            if r["source"] not in nodes:
                nodes[r["source"]] = {"id": r["source"], "label": r["source"][:20], "type": "unknown"}
            if r["target"] not in nodes:
                nodes[r["target"]] = {"id": r["target"], "label": r["target"][:20], "type": "unknown"}
            edges.append({"source": r["source"], "target": r["target"], "label": r["type"], "type": "RELATION"})

        elements = [{"data": n} for n in nodes.values()]

        seen_edges = set()
        for e in edges:
            edge_id = f"{e['source']}-{e['target']}-{e['label']}"
            if edge_id in seen_edges:
                continue
            if e['source'] not in nodes or e['target'] not in nodes:
                continue  # skip edges with missing nodes
            seen_edges.add(edge_id)
            elements.append({"data": {**e, "id": edge_id}})

        return {"elements": elements}

@app.get("/contradict")
def contradictions(entity: str):
    contradictions = detect_contradictions(entity)
    return contradictions

@app.get("/query")
def query_endpoint(question: str):
    return run_query(question)