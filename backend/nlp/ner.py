import spacy

nlp = spacy.load("en_core_web_sm")

ENTITY_LABELS = {
    "PERSON": "Person",
    "ORG": "Organization",
    "GPE": "Location", 
    "LOC": "Location",
    "DATE": "date",
    "TIME": "time",
    "CARDINAL": "number",
    "FAC": "facility",
}

def extract_entities(text: str) -> list[dict]:
    doc = nlp(text)
    entities = []
    seen = set()

    for ent in doc.ents:
        if ent.label_ not in ENTITY_LABELS:
            continue
        key = (ent.text, ent.label_)
        if key in seen:
            continue
        seen.add(key)
        entities.append({
            "text": ent.text.strip(),
            "type": ENTITY_LABELS[ent.label_],
            "original_label": ent.label_
        })
    return entities