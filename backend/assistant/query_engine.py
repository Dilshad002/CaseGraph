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

Always use 'DISTINCT' where appropriate to avoid duplicate results.
Return ONLY valid JSON. No explanation outside the JSON."""

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
                    {"role": "user", "content": f"Question: {question}\nData: {json.dumps(results)}\nAnswer the question in 1-2 sentences based on the data."}
                ],
                temperature=0,
                max_tokens=200
            )
            return {
                "type": "GRAPH_QUERY",
                "cypher": parsed["cypher"],
                # "results": results,
                "answer": summary_response.choices[0].message.content.strip()
            }
        except Exception as e:
            return {"type": "error", "message": str(e)}

    return parsed