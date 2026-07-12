import os
import json
from groq import Groq
from backend.graph.connection import get_session

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

SYSTEM_PROMPT = """You are an AI assistant for a criminal investigation support system.
You have access to a Neo4j knowledge graph containing criminal case data.

You can answer questions in two ways:

1. GRAPH_QUERY: If the question requires structured data lookup, respond with:
{"type": "GRAPH_QUERY", "cypher": "<valid Cypher query>"}

2. DIRECT_ANSWER: If you can answer from context provided, respond with:
{"type": "DIRECT_ANSWER", "answer": "<your answer>"}

Graph schema:
- (Case {fir_number, filename})
- (Entity {text, type}) — types: person, location, organization, phone_number, vehicle_number, time, date
- (TimeWindow {date, start, end, fir})
- (Case)-[:MENTIONS]->(Entity)
- (Entity)-[:RELATION {type, fir, source_span}]->(Entity)
- (Entity)-[:HAS_ATTRIBUTE {fir, attr}]->(Entity) — attrs: age, mobile
- (Entity)-[:ACCUSED_IN]->(Case)
- (Case)-[:INCIDENT_TIME]->(TimeWindow)
- (Case)-[:INCIDENT_LOCATION]->(Entity)

To find vehicles linked to a person, use:
    MATCH (p:Entity {text: $name})-[r:RELATION]->(v:Entity)
    WHERE r.type IN ['FLED_IN', 'ESCAPED_ON', 'DROVE', 'PARKED']
    RETURN DISTINCT v.text, r.type, r.fir, r.source_span

IMPORTANT: Vehicle descriptions like "white Hyundai i20" are stored with type 'unknown', NOT 'vehicle_number'. 
vehicle_number type is only for registration plates like 'KA03AB1122'.
When querying for vehicles linked to a person via FLED_IN, ESCAPED_ON etc, do NOT filter by type.

When querying both accused and complainant in the same query, use two separate MATCH clauses, NOT UNION:
MATCH (accused:Entity)-[:ACCUSED_IN]->(c:Case {fir_number: '203/2026'})
MATCH (complainant:Entity)-[:COMPLAINANT_IN]->(c)
RETURN accused.text AS accused, complainant.text AS complainant

When querying vehicles linked to a person, do NOT filter by entity type since some persons may be misclassified:
MATCH (e:Entity)-[r:RELATION]->(v:Entity)
WHERE toLower(e.text) = toLower('person name')
AND r.type IN ['FLED_IN', 'ESCAPED_ON', 'DROVE', 'PARKED', 'FLED_ON', 'ESCAPED_IN']
RETURN DISTINCT v.text, r.type, r.fir, r.source_span

If UNION is needed, all branches must return the same column names.

To find the complainant in a FIR, use:
MATCH (e:Entity)-[:COMPLAINANT_IN]->(c:Case {fir_number: $fir})
RETURN e.text AS complainant

To find the accused in a FIR, use:
MATCH (e:Entity)-[:ACCUSED_IN]->(c:Case {fir_number: '145/2026'})
RETURN e.text AS accused

For FIR summary queries, use this pattern instead of MENTIONS:
MMATCH (c:Case {fir_number: $fir})-[:MENTIONS]->(e:Entity)
WHERE e.type IN ['person', 'location', 'vehicle_number', 'phone_number']
RETURN DISTINCT e.text AS text, e.type AS type
UNION
MATCH (s:Entity)-[r:RELATION {fir: $fir}]->(o:Entity)
RETURN s.text + ' ' + r.type + ' ' + o.text AS text, 'relation' AS type

When querying relationships, always include r.source_span in the RETURN clause.

Always use 'DISTINCT' where appropriate to avoid duplicate results.
Return ONLY valid JSON. No explanation outside the JSON."""

NOISE_TYPES = {"number", "unknown", "date", "time"}

def filter_summary_entities(results: list[dict]) -> list[dict]:
    return [
        r for r in results
        if r.get("type") not in NOISE_TYPES
        and r.get("text", "").strip()
        and not r.get("text", "").strip().isdigit()
    ]

def run_cypher(cypher: str) -> list[dict]:
    with get_session() as session:
        result = session.run(cypher)
        return [dict(r) for r in result]

def query(question: str) -> dict:
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question}
        ],
        temperature=0,
        max_tokens=500
    )

    raw = response.choices[0].message.content.strip()
    start = raw.find("{")
    end = raw.rfind("}") + 1
    raw = raw[start:end]

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {"type": "error", "message": "Failed to parse LLM response", "raw": raw}

    if parsed.get("type") == "GRAPH_QUERY":
        try:
            results = run_cypher(parsed["cypher"])
            # Summarize results in natural language
            summary_response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "user", "content": f"""Question: {question}

                    Database returned these exact results: {json.dumps(results)}

                    Write one sentence that directly answers the question using ONLY the values in the results above.
                    Start your answer with the actual values from the results, not with "Based on" or "According to".
                    If the results are empty, say no results were found."""}
                        ],
                        temperature=0,
                        max_tokens=150
            )
            sources = []
            for r in results:
                span = r.get("source_span") or r.get("r.source_span") or r.get("span")
                if span:
                    sources.append(span)

            return {
                "type": "GRAPH_QUERY",
                "cypher": parsed["cypher"],
                "results": results,
                "answer": summary_response.choices[0].message.content.strip(),
                "sources": [s for s in sources if s]
            }
        
        except Exception as e:
            return {"type": "error", "message": str(e)}
        
    return parsed