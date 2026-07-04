# CaseGraph

CaseGraph extracts structured information from First Information Reports (FIRs) and writes it into a Neo4j knowledge graph. It combines OCR/PDF text extraction, NER, regex-based structured field extraction, and LLM-based relationship extraction to turn unstructured police report text into a queryable graph of entities and their relationships.

**Status: Work in progress.** Core extraction and graph-write pipelines are functional and tested. Currently in active development: contradiction detection across relationships and documents.

---

## What it does

1. Accepts a FIR as a PDF or image upload.
2. Extracts raw text via PyMuPDF (PDF) or Tesseract OCR (image).
3. Cleans and normalizes the extracted text.
4. Runs spaCy NER to identify entities (people, organizations, locations, etc.).
5. Runs regex extraction for structured identifiers (phone numbers, vehicle registrations, IMEI, Aadhaar, PAN, IFSC, UPI IDs, bank accounts, passport numbers).
6. Sends the cleaned text to a Groq-hosted Llama 3.3 70B model to extract factual relationships between entities (e.g., `PARKED`, `FLED_IN`, `CARRIED`, `REPORTED_STOLEN`, `CONFRONTED`).
7. Verifies each extracted relationship against the source text — checking that the stated relation type is lexically supported by the span, that subject/object are actually grounded in the span (including role-reference resolution, e.g. "the accused" → the accused's name), and that the span is a verbatim substring of the source document.
8. Writes verified entities and relationships to a Neo4j graph, scoped per case.

---

## Tech stack

- **API**: FastAPI
- **PDF/OCR**: PyMuPDF, pytesseract
- **NLP**: spaCy (`en_core_web_sm`)
- **Relationship extraction**: Groq API, Llama 3.3 70B
- **Graph database**: Neo4j
- **Dependency management**: uv

---

## Setup

### Requirements

- Python >= 3.14
- A running Neo4j instance
- A Groq API key ([console.groq.com](https://console.groq.com))
- Tesseract OCR installed on your system (required by `pytesseract`)

### Install dependencies

This project uses [uv](https://docs.astral.sh/uv/) for dependency management.

```bash
uv sync
```

This installs all dependencies listed in `pyproject.toml`, including the spaCy `en_core_web_sm` model.

### Environment variables

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

```
GROQ_API_KEY=your_groq_api_key_here

NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password_here
```

### Run Neo4j

Point `NEO4J_URI` at any running Neo4j instance (local Desktop install, Docker, or Aura). Default local bolt port is `7687`; Neo4j Browser is typically at `http://localhost:7474`.

### Run the API

```bash
uvicorn backend.main:app --reload
```

The API will be available at `http://localhost:8000`.

---

## API

### `GET /health`

Health check.

```bash
curl http://localhost:8000/health
```

```json
{"status": "healthy"}
```

### `POST /extract`

Upload a FIR (PDF or image) for extraction and graph write.

```bash
curl -X POST "http://localhost:8000/extract" \
  -F "file=@/path/to/fir.pdf"
```

**Response:**

```json
{
  "filename": "fir1.pdf",
  "cleaned_text": "...",
  "entities": [
    {"text": "Rohan Kumar", "type": "person", "original_label": "PERSON"}
  ],
  "regex_entities": {
    "phone_numbers": ["9876543210"],
    "vehicle_numbers": ["KA01MN4589"],
    "fir_number": "145/2026",
    "imei_numbers": [],
    "aadhaar_numbers": [],
    "pan_numbers": [],
    "ifsc_codes": [],
    "passport_numbers": [],
    "upi_ids": [],
    "bank_accounts": [],
    "driving_licences": []
  },
  "relationships": [
    {
      "subject": "Rohan Kumar",
      "relation": "PARKED",
      "object": "Toyota Innova Crysta",
      "source_span": "The complainant stated that he had parked his Toyota Innova Crysta ..."
    }
  ]
}
```

This request also writes the extracted case, entities, and relationships to Neo4j as a side effect.

---

## Graph model

- `(:Case {fir_number, filename, id})` — one node per uploaded FIR.
- `(:Entity {text, type, case_key?})` — extracted entities. Entities with globally unique identifier types (vehicle number, phone number, IMEI, Aadhaar, PAN, passport, UPI ID, bank account, IFSC) are shared across cases. All other entity types are scoped per-case via `case_key`.
- `(:Case)-[:MENTIONS]->(:Entity)` — links a case to every entity it mentions.
- `(:Entity)-[:RELATION {type, fir, source_span}]->(:Entity)` — a verified factual relationship extracted from the document text, with the relation type and supporting source span attached as edge properties.

### Viewing the graph

In Neo4j Browser:

```cypher
MATCH (c:Case)-[m:MENTIONS]->(e:Entity)
OPTIONAL MATCH (e)-[r:RELATION]->(o:Entity)
RETURN c, m, e, r, o
```

Switch to the **Graph** view (not Table) to see it visually. If entity nodes render with the wrong label, set the node caption for the `Entity` label to `{text}` in Neo4j Browser's style settings.

---

## Project structure

```
backend/
├── ingestion/       # PDF/OCR text extraction, text cleaning
├── nlp/             # NER, regex-based structured extraction, field stripping
├── reasoning/        # LLM-based relationship extraction and verification
├── graph/           # Neo4j connection and write logic
└── main.py          # FastAPI app and /extract endpoint
```

---

## Roadmap

- Contradiction detection across relationships and documents (in progress).

---

## Vision / Planned Architecture

The current implementation handles single-document FIR extraction end-to-end (OCR/text → NER → relationship extraction → Neo4j). The longer-term system extends this to a multi-source investigation platform:

### Planned input types

- Scanned documents (FIRs, witness statements, police reports) — via OCR
- Digital text documents
- Call logs (structured/CSV)
- GPS logs (structured/CSV)

### Planned pipeline

```
Raw Evidence
     │
     ▼
OCR + Text Extraction
     │
     ▼
NLP Processing
(Entity extraction — people, places, times, vehicles, phone numbers)
(Relationship extraction — "A called B", "X was at Y")
     │
     ▼
Knowledge Graph (Neo4j)
     │
     ├──► Timeline Reconstruction
     │
     ├──► Contradiction Detection
     │    (cross-reference entities + timestamps across sources)
     │
     └──► Query Interface (LLM + RAG over graph)
               │
               ▼
        Investigation Dashboard (React)
```

### Planned tech stack additions

- PostgreSQL — raw evidence storage
- FAISS — similar-case retrieval via embeddings
- React — frontend dashboard

### Planned outputs

- Entity-relationship graph (visual)
- Chronological timeline
- Contradiction report
- Natural language query answers with evidence citations
- Case summary report

