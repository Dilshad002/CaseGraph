from backend.graph.connection import get_session
from datetime import datetime

def parse_time(t: str) -> datetime:
    if not t:
        return None
    for fmt in ["%I:%M %p", "%I:%M%p"]:
        try:
            return datetime.strptime(t.strip().upper(), fmt)
        except ValueError:
            continue
    return None

def times_overlap(start1: str, end1: str, start2: str, end2: str) -> bool:
    s1, e1 = parse_time(start1), parse_time(end1)
    s2, e2 = parse_time(start2), parse_time(end2)
    if not all([s1, s2]):
        return False
    e1 = e1 or s1
    e2 = e2 or s2
    return s1 <= e2 and s2 <= e1

def get_entity_appearances(entity_text: str) -> list[dict]:
    #Get all cases that mention a specific entity.
    with get_session() as session:
        result = session.run(
            """
            MATCH (c:Case)-[:MENTIONS]->(e:Entity {text: $text})
            RETURN c.fir_number AS fir_number, c.filename AS filename, e.type AS entity_type
            """,
            text=entity_text
        )
        return [dict(r) for r in result]

def get_relations_for_entity(entity_text: str) -> list[dict]:
    #Get all relationships where this entity is subject or object, across all cases.
    with get_session() as session:
        result = session.run(
            """
            MATCH (s:Entity {text: $text})-[r:RELATION]->(o:Entity)
            RETURN s.text AS subject, r.type AS relation, o.text AS object,
                   r.source_span AS source_span, r.fir AS fir_number
            UNION
            MATCH (s:Entity)-[r:RELATION]->(o:Entity {text: $text})
            RETURN s.text AS subject, r.type AS relation, o.text AS object,
                   r.source_span AS source_span, r.fir AS fir_number
            """,
            text=entity_text
        )
        return [dict(r) for r in result]
    
def detect_attribute_contradictions(entity_text: str) -> list[dict]:
    with get_session() as session:
        result = session.run(
            """
            MATCH (p:Entity {text: $name})-[r:HAS_ATTRIBUTE]->(a:Entity)
            RETURN r.attr AS attribute, a.text AS value, r.fir AS fir_number
            """,
            name=entity_text
        )
        rows = [dict(r) for r in result]

    grouped = {}
    for row in rows:
        attr = row["attribute"]
        if attr not in grouped:
            grouped[attr] = {}
        grouped[attr][row["fir_number"]] = row["value"]

    contradictions = []
    for attr, fir_values in grouped.items():
        unique_values = set(fir_values.values())
        if len(unique_values) > 1:
            contradictions.append({
                "attribute": attr,
                "conflict": fir_values
            })

    return contradictions

def detect_contradictions(entity_text: str) -> dict:
    appearances = get_entity_appearances(entity_text)
    relations = get_relations_for_entity(entity_text)
    attribute_contradictions = detect_attribute_contradictions(entity_text)

    if len(appearances) < 2:
        return {
            "entity": entity_text,
            "appears_in": appearances,
            "contradictions": [],
            "message": "Entity appears in only one case — no cross-case comparison possible."
        }

    contradictions = []

    # Relation-type conflicts
    relation_groups = {}
    for rel in relations:
        key = rel["relation"]
        if key not in relation_groups:
            relation_groups[key] = []
        relation_groups[key].append(rel)

    for relation_type, rels in relation_groups.items():
        fir_objects = {}
        for rel in rels:
            fir = rel["fir_number"]
            obj = rel["object"]
            if fir not in fir_objects:
                fir_objects[fir] = set()
            fir_objects[fir].add(obj)

        all_objects = [obj for objs in fir_objects.values() for obj in objs]
        if len(set(all_objects)) > 1 and len(fir_objects) > 1:
            contradictions.append({
                "type": "relation_conflict",
                "relation": relation_type,
                "conflict": {fir: list(objs) for fir, objs in fir_objects.items()},
                "supporting_spans": [
                    {"fir": r["fir_number"], "span": r["source_span"]}
                    for r in rels
                ]
            })

    # Attribute conflicts
    for attr_conflict in attribute_contradictions:
        contradictions.append({
            "type": "attribute_conflict",
            "attribute": attr_conflict["attribute"],
            "conflict": attr_conflict["conflict"]
        })

    temporal_contradictions = detect_temporal_spatial_contradictions(entity_text)
    contradictions.extend(temporal_contradictions)

    return {
        "entity": entity_text,
        "appears_in": appearances,
        "contradictions": contradictions
    }

def detect_temporal_spatial_contradictions(entity_text: str) -> list[dict]:
    with get_session() as session:
        result = session.run(
            """
            MATCH (p:Entity {text: $name})-[:ACCUSED_IN]->(c1:Case)-[:INCIDENT_TIME]->(t1:TimeWindow),
                  (c1)-[:INCIDENT_LOCATION]->(l1:Entity),
                  (p)-[:ACCUSED_IN]->(c2:Case)-[:INCIDENT_TIME]->(t2:TimeWindow),
                  (c2)-[:INCIDENT_LOCATION]->(l2:Entity)
            WHERE c1.fir_number < c2.fir_number
            AND t1.date = t2.date
            AND l1.text <> l2.text
            RETURN c1.fir_number AS fir1, l1.text AS location1, t1.start AS start1, t1.end AS end1,
                   c2.fir_number AS fir2, l2.text AS location2, t2.start AS start2, t2.end AS end2,
                   t1.date AS date
            """,
            name=entity_text
        )
        rows = [dict(r) for r in result]

    contradictions = []
    for row in rows:
        if times_overlap(row["start1"], row["end1"], row["start2"], row["end2"]):
            contradictions.append({
                "type": "temporal_spatial_conflict",
                "date": row["date"],
                "conflict": {
                    row["fir1"]: {"location": row["location1"], "time": f"{row['start1']} - {row['end1']}"},
                    row["fir2"]: {"location": row["location2"], "time": f"{row['start2']} - {row['end2']}"}
                }
            })
    return contradictions