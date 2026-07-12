# CaseGraph

An AI-powered criminal investigation support system that ingests FIR documents, extracts entities and relationships, builds a temporal knowledge graph, detects contradictions across sources, and provides explainable investigative insights via natural language queries.

CaseGraph augments human investigators by eliminating manual evidence correlation. Every output is traceable back to its source document. No black-box conclusions.

---

## Problem

Criminal investigations involve large volumes of heterogeneous evidence — FIRs, witness statements, call logs, forensic reports. Investigators manually cross-reference this across documents, which is slow, error-prone, and misses connections that span multiple cases.

Existing case management tools store and retrieve evidence. They do not reason over it.

---

## What CaseGraph Does

- Ingests scanned documents via OCR and digital PDFs
- Extracts 11 types of structured identifiers (phone, vehicle, IMEI, Aadhaar, PAN, IFSC, UPI, bank account, passport, driving licence, FIR number) using regex
- Extracts named entities (persons, locations, organizations, times) using spaCy NER
- Extracts relationships from narrative text using an LLM with hallucination guards
- Builds a temporal knowledge graph in Neo4j connecting entities across documents
- Detects contradictions across FIRs: attribute conflicts (age, mobile), relation conflicts (fled in different vehicles), temporal-spatial conflicts (same person at two locations during overlapping time windows)
- Answers natural language queries with graph-backed Cypher and source attribution
- Provides a dark forensic-themed React dashboard with graph visualization

---

## Architecture

```
                        Evidence Upload (PDF / Image)
                                    │
                    ┌───────────────┼───────────────┐
                    │                               │
              PDF Extraction                   OCR (Tesseract)
              (PyMuPDF)                             │
                    └───────────────┬───────────────┘
                                    │
                              Text Cleaning
                          (Unicode, whitespace,
                           field label stripping)
                                    │
                    ┌───────────────┼───────────────┐
                    │                               │
             Regex Extraction                spaCy NER
          (11 identifier types)         (persons, locations,
                    │                    orgs, times, dates)
                    └───────────────┬───────────────┘
                                    │
                         Deduplication & Overlap
                              Stripping
                                    │
                    ┌───────────────┼───────────────┐
                    │                               │
             LLM Relation               Person Attribute
             Extraction                  Extraction
          (Groq / llama-3.3)          (age, mobile from
          with hallucination            structured fields)
              guards                        │
                    │                       │
                    └───────────────┬───────────────┘
                                    │
                              Neo4j Graph
                         ┌──────────────────┐
                         │  Case Nodes       │
                         │  Entity Nodes     │
                         │  MENTIONS edges   │
                         │  RELATION edges   │
                         │  HAS_ATTRIBUTE    │
                         │  ACCUSED_IN       │
                         │  COMPLAINANT_IN   │
                         │  INCIDENT_TIME    │
                         │  INCIDENT_LOCATION│
                         └──────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
            Contradiction      Natural Language    Graph
             Detection          Query Engine    Visualization
          (attribute,          (LLM → Cypher →  (Cytoscape.js)
           relation,            Answer + Source
           temporal-spatial)    Attribution)
                    │               │               │
                    └───────────────┴───────────────┘
                                    │
                           React Frontend
                    (Upload · Graph · Contradictions · Query)
```

---

## Graph Schema

```
(Case {fir_number, filename, id})
(Entity {text, type, case_key})
(TimeWindow {date, start, end, fir})

(Case)-[:MENTIONS]->(Entity)
(Entity)-[:RELATION {type, fir, source_span}]->(Entity)
(Entity)-[:HAS_ATTRIBUTE {fir, attr}]->(Entity)
(Entity)-[:ACCUSED_IN]->(Case)
(Entity)-[:COMPLAINANT_IN]->(Case)
(Case)-[:INCIDENT_TIME]->(TimeWindow)
(Case)-[:INCIDENT_LOCATION]->(Entity)
```

Entity types: `person`, `location`, `organization`, `vehicle_number`, `phone_number`, `facility`, `date`, `time`

Global entity types (shared across FIRs for cross-case linking): `person`, `vehicle_number`, `phone_number`, `imei`, `aadhaar`, `pan`, `passport`, `upi_id`, `bank_account`, `ifsc`

---

## Contradiction Detection

Three types of contradiction are detected on-demand across FIRs:

**Attribute conflicts** — same person with different age or mobile number across FIRs.
```
Vikram Reddy: age 34 (FIR 145/2026) vs age 32 (FIR 152/2026)
Vikram Reddy: mobile 9123456789 (FIR 145/2026) vs 9876501234 (FIR 178/2026)
```

**Relation conflicts** — same person, same relation type, different object across FIRs.
```
Vikram Reddy FLED_IN Hyundai i20 (FIR 145/2026)
Vikram Reddy FLED_IN Mahindra Thar (FIR 178/2026)
```
Every conflict includes the exact source span from the original document.

**Temporal-spatial conflicts** — same person placed at two different locations during overlapping time windows on the same date.
```
Vikram Reddy at Phoenix Marketcity, 08:15–08:45 PM (FIR 145/2026)
Vikram Reddy at Indiranagar, 08:20–08:40 PM (FIR 152/2026)
Date: 28/06/2026
```

---

## Query Interface

Natural language queries are translated to Cypher by an LLM, executed against the graph, and summarized back in plain English. Every answer includes the Cypher query used (source attribution) and relevant source spans where available.

Example queries:
- `Who are all accused persons across all FIRs?`
- `What vehicles are linked to Vikram Reddy?`
- `Which phone numbers appear in more than one FIR?`
- `Summarize FIR 145/2026`
- `Who is the complainant in FIR 203/2026?`

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI |
| OCR | Tesseract (pytesseract) |
| PDF extraction | PyMuPDF (fitz) |
| NLP / NER | spaCy (`en_core_web_md`) |
| LLM | Groq (`llama-3.3-70b-versatile`) |
| Graph database | Neo4j 5 |
| Frontend | React + TypeScript |
| Graph visualization | Cytoscape.js (react-cytoscapejs) |
| UI components | shadcn/ui (Radix, Nova preset) |
| Styling | Tailwind CSS v4 |
| HTTP client | Axios |
| Routing | React Router |
| Package manager (Python) | uv |
| Package manager (JS) | npm |

---

## Project Structure

```
CaseGraph/
├── backend/
│   ├── main.py                         # FastAPI app, all endpoints
│   ├── ingestion/
│   │   ├── ocr.py                      # Tesseract OCR
│   │   ├── pdf_extractor.py            # PyMuPDF text extraction
│   │   └── cleaner.py                  # Text normalization
│   ├── nlp/
│   │   ├── ner.py                      # spaCy NER pipeline
│   │   ├── regex_extractor.py          # 11-type identifier extraction
│   │   └── field_stripper.py           # Section header removal before NER
│   ├── graph/
│   │   ├── connection.py               # Neo4j driver
│   │   └── writer.py                   # Graph write operations
│   ├── reasoning/
│   │   ├── relation_extractor.py       # LLM relation extraction with guards
│   │   └── contradiction_detection.py  # Cross-FIR contradiction detection
│   └── assistant/
│       └── query_engine.py             # NL → Cypher → Answer pipeline
├── frontend/
│   └── src/
│       ├── App.tsx                     # Layout, routing, sidebar
│       ├── pages/
│       │   ├── UploadPage.tsx          # Document upload + extraction results
│       │   ├── GraphPage.tsx           # Cytoscape knowledge graph
│       │   ├── ContradictionsPage.tsx  # Contradiction search + display
│       │   └── QueryPage.tsx           # Chat-style query interface
│       └── store/
│           └── AppContext.tsx          # Upload history state
├── tests/
│   ├── test_nlp.py
│   ├── test_extractors.py
│   ├── test_contradiction.py
│   └── test_query_engine.py
├── pyproject.toml
└── README.md
```

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Service health check |
| POST | `/extract` | Upload document, extract entities, write to graph |
| GET | `/graph` | Fetch all nodes and edges for visualization |
| GET | `/contradict?entity=` | Detect contradictions for a named entity |
| GET | `/query?question=` | Natural language query over graph |
| DELETE | `/case?fir_number=` | Delete a case and orphaned entities |

---

## Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- [uv](https://github.com/astral-sh/uv)
- Tesseract OCR (system package)
- Neo4j 5 (native install or Docker)
- Groq API key — free tier at [console.groq.com](https://console.groq.com)

### Backend

```bash
git clone https://github.com/Dilshad002/casegraph.git
cd casegraph

uv add fastapi uvicorn python-multipart pytesseract pillow pymupdf spacy groq neo4j python-dotenv
uv add https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl

# Ubuntu/Debian
sudo apt install tesseract-ocr

cp .env.example .env
# Set GROQ_API_KEY, NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

sudo systemctl start neo4j
uvicorn backend.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend at `http://localhost:5173` · API at `http://localhost:8000`

---

## Tests

```bash
uv run pytest tests/ -v
```

43 tests covering NER extraction, regex extraction (FIR number, phone, vehicle, person attributes, incident details), contradiction detection (attribute, temporal-spatial, time overlap logic), and query engine with mocked Groq and Neo4j.

---

## Known Limitations

- spaCy `en_core_web_md` occasionally misclassifies entity types (e.g. organization names tagged as persons). The dedicated regex extractor is the source of truth for structured identifiers — phone numbers, vehicle plates, and other identifiers extracted by regex take precedence over NER output.
- Relation names extracted by the LLM are not normalized — `FLED_IN` and `ESCAPED_ON` are treated as different relation types even if semantically equivalent. Contradiction detection on relation type requires exact string match.
- The query engine generates Cypher via LLM. Complex or ambiguous queries may produce invalid Cypher; errors are returned to the user with the raw message.
- API key authentication is implemented but the key is transmitted in plaintext via HTTP headers. Suitable for local use only. Production deployment requires JWT-based authentication over HTTPS.

---

## Research Contribution

The novelty is not in using AI individually but in integrating multiple AI techniques into an explainable reasoning framework:

- A unified document processing pipeline handling both digital and scanned evidence
- A temporal knowledge graph built from heterogeneous evidence, with FIR-scoped entity deduplication and cross-FIR global entity linking
- Three classes of automatic contradiction detection across independent evidence streams
- Explainable AI — every relationship is stored with its source span, every query answer includes the Cypher used to generate it, every contradiction is linked to the exact document text that supports it

---

## Author

Dilshad

GitHub: [Dilshad002](https://github.com/Dilshad002)