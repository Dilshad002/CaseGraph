import json
import os
import re
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

RELATION_EXTRACTION_PROMPT = """You extract factual relationships between entities from a criminal investigation document (FIR).
Only use a relation type if the source_span contains language that directly states that relationship. 
Only assert OWNS when the text uses direct possessive language (his/her/their + noun) or explicit ownership language (belonging to, owned by). 
Do not assert OWNS from an entity merely being listed near another (e.g. under 'Recovered Evidence')."

Rules:
- Only extract relationships EXPLICITLY stated in the text. Do not infer, assume, or add anything not directly written.
- Every relationship MUST include the exact verbatim text span from the document that supports it.
- If you are not certain a relationship is explicitly stated, do not include it.
- Return ONLY valid JSON, no preamble, no markdown fences.

Entities found in this document:
{entities}

Document text:
{text}

Return a JSON array of relationships in this exact format:
[
  {{
    "subject": "entity text",
    "relation": "short verb phrase, e.g. VISITED, FLED_IN, OWNS, CALLED, REPORTED_STOLEN",
    "object": "entity text",
    "source_span": "exact verbatim quote from the document proving this relationship"
  }}
]

If no relationships are found, return [].
"""

def _normalize_whitespace(s: str) -> str:
    return re.sub(r'\s+', ' ', s).strip()

def extract_relationships(text: str, entity_texts: list[str]) -> list[dict]:
    prompt = RELATION_EXTRACTION_PROMPT.format(
        entities=", ".join(entity_texts),
        text=text
    )

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=2000,
    )

    raw = response.choices[0].message.content.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()

    try:
        relationships = json.loads(raw)
    except json.JSONDecodeError:
        return []

    return relationships

def verify_relationships(relationships: list[dict], source_text: str) -> list[dict]:
    normalized_source = _normalize_whitespace(source_text)
    verified = []
    for rel in relationships:
        span = rel.get("source_span", "").strip()
        if not span:
            continue
        if _normalize_whitespace(span) not in normalized_source:
            continue
        verified.append(rel)
    return verified