import json
import os
import re
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

RELATION_EXTRACTION_PROMPT = '''You are an information extraction system.

Your task is to extract factual relationships between entities from a criminal investigation document (FIR).

Your goal is to capture ONLY relationships that are explicitly stated in the text.

-----------------------
GENERAL PRINCIPLES
-----------------------

1. Never infer facts.

Do not strengthen, reinterpret, or speculate beyond what is explicitly written.

2. Every relationship must be directly supported by the source_span.

The source_span must, by itself, justify the extracted relationship.

3. Preserve meaning.

Choose the relation that most accurately reflects the wording used in the source_span.

Do not replace a weaker relationship with a stronger one.

4. If the evidence is ambiguous, do not extract a relationship.

Returning fewer relationships is preferable to returning incorrect ones.

5. Use only entities that already exist in the supplied entity list whenever possible.

Do not invent new entities.

Do not paraphrase entity names if an equivalent extracted entity already exists.

6. Copy the source_span exactly from the document.

Do not rewrite or summarize it.

7, If a single sentence contains multiple distinct factual relationships (e.g., x confronted y, and y fled in a car), 
extract each one as a separate relationship object, each with its own precise source_span covering only that clause.

-----------------------
RELATION SELECTION
-----------------------

The relation should represent the action or fact explicitly expressed in the supporting text.

The relation should not express implications that are not directly stated.

For example:

- movement does not imply ownership
- possession does not necessarily imply ownership
- proximity does not imply association
- mention does not imply involvement

Choose the most specific relation supported by the evidence.

-----------------------
OUTPUT
-----------------------

Return a JSON array of relationships in this exact format:
[
  {{
    "subject": "entity text",
    "relation": "short verb phrase, e.g. VISITED, FLED_IN, OWNS, CALLED, REPORTED_STOLEN",
    "object": "entity text",
    "source_span": "exact verbatim quote from the document proving this relationship"
  }}
]

If no relationships are explicitly stated, return [].

-----------------------
KNOWN ENTITIES
-----------------------

{entities}

-----------------------
DOCUMENT
-----------------------

{text}
'''

RELATION_KEYWORDS = {
    "OWNS": [
        "belonging to",
        "owned by",
        "their ",
        "registered in the name of"
    ],

    "FLED_IN": [
        "fled",
        "escaped",
        "drove away",
        "sped away"
    ],

    "CARRIED": [
        "carrying",
        "carried",
        "holding"
    ],

    "PARKED": [
        "parked"
    ],

    "REPORTED_STOLEN": [
        "reported stolen",
        "was stolen",
        "were stolen"
    ],

    "CONFRONTED": [
        "confronted"
    ]
}

RELATION_ALIASES = {
    "OWNED": "OWNS",
    "OWNING": "OWNS",
    "CARRIED": "CARRIED",
    "FLED": "FLED_IN",
}

def build_role_map(text: str) -> dict:
    complainant = re.search(r"Complainant\s*(?:Details)?.*?Name:\s*(.+)", text, re.DOTALL)
    accused = re.search(r"Accused\s*(?:Details)?.*?Name:\s*(.+)", text, re.DOTALL)

    role_map = {}
    if complainant:
        name = complainant.group(1).split("\n")[0].strip()
        role_map[name] = {"unambiguous": {"the complainant"}}
    if accused:
        name = accused.group(1).split("\n")[0].strip()
        role_map[name] = {"unambiguous": {"the accused"}}
    return role_map

def _canonical_relation(relation: str) -> str:
    r = relation.upper().strip()
    # normalize common verb endings so OWNED/OWNS/OWNING map to one key
    if r.endswith("ED") and r[:-2] in RELATION_KEYWORDS:
        return r[:-2]
    if r.endswith("D") and r[:-1] in RELATION_KEYWORDS:
        return r[:-1]
    if r.endswith("ING") and r[:-3] in RELATION_KEYWORDS:
        return r[:-3]
    return r

def relation_supported(relation, span):
    span = span.lower()

    canon = _canonical_relation(relation)
    canon = RELATION_ALIASES.get(canon, canon)

    keywords = RELATION_KEYWORDS.get(canon)
    if keywords is None:
        return False

    return any(k in span for k in keywords)

def _normalize_whitespace(s: str) -> str:
    return re.sub(r'\s+', ' ', s).strip()

def extract_relationships(text: str, entity_texts: list[str]) -> list[dict]:
    role_map = build_role_map(text)
    print("ROLE MAP:", role_map)
    prompt = RELATION_EXTRACTION_PROMPT.format(entities=", ".join(entity_texts), text=text)
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
    except json.JSONDecodeError as e:
        print("PARSE FAILED:", e)
        print("RAW LLM OUTPUT:", raw)
        return []
    
    relationships = verify_relationships(relationships, text, role_map)

    return relationships

def relation_grounded(subject, obj, span, role_map):
    span_lower = span.lower()

    def check(entity):
        if entity.lower() in span_lower:
            return True
        entity_parts = [p.lower() for p in entity.split() if len(p) > 2]
        span_words = set(re.findall(r"\b\w+\b", span_lower))
        if any(part in span_words for part in entity_parts):
            return True
        refs = role_map.get(entity, {}).get("unambiguous", set())
        return any(r in span_lower for r in refs)

    return check(subject) and check(obj)

def verify_relationships(relationships: list[dict], source_text: str, role_map: dict) -> list[dict]:
    normalized_source = _normalize_whitespace(source_text)
    verified = []

    for rel in relationships:
        span = rel.get("source_span", "").strip()
        if not span:
            continue

        subject = rel.get("subject", "")
        obj = rel.get("object", "")
        relation = rel.get("relation", "")

        if not relation_supported(relation, span):
            continue
        if not relation_grounded(subject, obj, span, role_map):
            continue
        if _normalize_whitespace(span) not in normalized_source:
            continue

        verified.append(rel)
    return verified