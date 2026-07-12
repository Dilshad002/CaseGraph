import uuid
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from backend.ingestion.ocr import extract_text_from_image
from backend.ingestion.cleaner import clean_text
from backend.ingestion.pdf_extractor import extract_text_from_pdf
from backend.nlp.ner import extract_entities
from backend.nlp.regex_extractor import extract_regex_entities, strip_overlapping_ner_entities, extract_person_attributes
from backend.graph.writer import write_extractions_to_graph, write_relationships_to_graph, write_person_attributes, write_incident_to_graph
from backend.nlp.field_stripper import strip_field_labels
from backend.reasoning.relation_extractor import extract_relationships, build_role_map
from backend.reasoning.contradiction_detection import detect_contradictions
from backend.assistant.query_engine import query as run_query
from backend.graph.connection import get_session
from backend.assistant.query_engine import client as groq_client
from backend.nlp.regex_extractor import extract_incident_details_llm

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
    regex_entities = extract_regex_entities(cleaned_text)

    ner_input = strip_field_labels(cleaned_text)
    entities = extract_entities(ner_input)
    entities = strip_overlapping_ner_entities(entities, regex_entities)

    entity_texts = [e["text"] for e in entities] + \
        regex_entities.get("phone_numbers", []) + \
        regex_entities.get("vehicle_numbers", [])

    relationships = extract_relationships(cleaned_text, entity_texts)

    case_id = str(uuid.uuid4())
    fir_number = regex_entities.get("fir_number")
    print(f"Extracted FIR number: {fir_number}")

    write_extractions_to_graph(case_id, file.filename, entities, regex_entities)
    write_relationships_to_graph(case_id, relationships, file.filename, entities, fir_number)

    role_map = build_role_map(cleaned_text)
    person_attrs = extract_person_attributes(cleaned_text, role_map)

    for p in person_attrs:
        write_person_attributes(p["name"], p["attributes"], fir_number, file.filename)

    accused_name = None
    complainant_name = None
    for name, data in role_map.items():
        refs = data.get("unambiguous", set())
        if "accused" in refs:
            accused_name = name
        if "complainant" in refs:
            complainant_name = name
    print(f"Accused: {accused_name}, Complainant: {complainant_name}")

    incident = extract_incident_details_llm(cleaned_text, groq_client, "llama-3.3-70b-versatile")
    print(f"INCIDENT LLM: {incident}")
    write_incident_to_graph(fir_number, incident, accused_name, complainant_name)

    return {
        "filename": file.filename,
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

        result = session.run("MATCH (c:Case) RETURN c.fir_number AS fir_number, c.filename AS filename")
        for r in result:
            fir = r["fir_number"]
            nodes[fir] = {"id": fir, "label": f"FIR {fir}", "type": "Case"}

        result = session.run("""
            MATCH (c:Case)-[:MENTIONS]->(e:Entity)
            WHERE e.type IN ['person', 'location', 'vehicle_number', 'phone_number', 'facility']
            RETURN DISTINCT e.text AS id, e.type AS type, c.fir_number AS fir
        """)
        for r in result:
            if r["id"] not in nodes:
                label = r["id"][:20] + "..." if len(r["id"]) > 20 else r["id"]
                nodes[r["id"]] = {"id": r["id"], "label": label, "type": r["type"]}
            edges.append({"source": r["fir"], "target": r["id"], "label": "MENTIONS", "type": "MENTIONS"})

        result = session.run("""
            MATCH (s:Entity)-[r:RELATION]->(o:Entity)
            WHERE s.type IN ['person', 'location', 'vehicle_number', 'phone_number', 'facility']
            OR o.type IN ['person', 'location', 'vehicle_number', 'phone_number', 'facility']
            RETURN s.text AS source, o.text AS target, r.type AS type
        """)
        for r in result:
            if r["source"] in nodes and r["target"] in nodes:
                edges.append({"source": r["source"], "target": r["target"], "label": r["type"], "type": "RELATION"})

        elements = [{"data": n} for n in nodes.values()]

        seen_edges = set()
        for e in edges:
            edge_id = f"{e['source']}-{e['target']}-{e['label']}"
            if edge_id in seen_edges:
                continue
            if e['source'] not in nodes or e['target'] not in nodes:
                continue
            seen_edges.add(edge_id)
            elements.append({"data": {**e, "id": edge_id}})

        return {"elements": elements}

@app.delete("/case")
def delete_case(fir_number: str):
    with get_session() as session:
        session.run(
            """
            MATCH (c:Case {fir_number: $fir_number})
            DETACH DELETE c
            """,
            fir_number=fir_number
        )
        session.run(
            """
            MATCH (e:Entity)
            WHERE NOT EXISTS {
                MATCH (c:Case)-[:MENTIONS]->(e)
            }
            AND NOT EXISTS {
                MATCH (e)-[:ACCUSED_IN]->(:Case)
            }
            AND NOT EXISTS {
                MATCH (e)-[:COMPLAINANT_IN]->(:Case)
            }
            DETACH DELETE e
            """
        )
        session.run(
            """
            MATCH (t:TimeWindow)
            WHERE NOT EXISTS {
                MATCH ()-[:INCIDENT_TIME]->(t)
            }
            DELETE t
            """
        )
    return {"deleted": fir_number}

@app.get("/contradict")
def contradictions(entity: str):
    return detect_contradictions(entity)

@app.get("/query")
def query_endpoint(question: str):
    return run_query(question)