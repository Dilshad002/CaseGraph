from backend.graph.connection import get_session

GLOBAL_TYPES = {
    "vehicle_number", "phone_number", "imei", "aadhaar",
    "pan", "passport", "upi_id", "bank_account", "ifsc"
}

def write_person_attributes(person_name: str, attributes: dict, fir_number: str, filename: str):
    #Write age, address as FIR-scoped relationships from a person node.
    with get_session() as session:
        for attr_type, attr_value in attributes.items():
            if not attr_value:
                continue
            session.run(
            """
            MERGE (p:Entity {text: $name, type: 'person'})
            MERGE (a:Entity {text: $value, type: $attr_type})
            MERGE (p)-[r:HAS_ATTRIBUTE {fir: $fir_number, attr: $attr_type, person: $name}]->(a)
            SET r.source = $filename
            """,
            name=person_name, value=str(attr_value),
            attr_type=attr_type, fir_number=fir_number, filename=filename
        )

def create_case_node(case_id: str, filename: str, fir_number: str = None):
    with get_session() as session:
        if fir_number:
            session.run(
                """
                MERGE (c:Case {fir_number: $fir_number})
                ON CREATE SET c.id = $case_id, c.filename = $filename
                """,
                case_id=case_id, filename=filename, fir_number=fir_number
            )
        else:
            session.run(
                """
                MERGE (c:Case {filename: $filename})
                SET c.id = $case_id
                """,
                case_id=case_id, filename=filename
            )


def create_entity_node(entity_text: str, entity_type: str, fir_number: str = None, filename: str = None):
    with get_session() as session:
        if fir_number:
            match_clause = "MATCH (c:Case {fir_number: $fir_number})"
        else:
            match_clause = "MATCH (c:Case {filename: $filename})"

        case_key = fir_number or filename

        if entity_type in GLOBAL_TYPES:
            merge_key = "MERGE (e:Entity {text: $text, type: $type})"
        else:
            merge_key = "MERGE (e:Entity {text: $text, type: $type, case_key: $case_key})"

        session.run(
            f"""
            {merge_key}
            WITH e
            {match_clause}
            MERGE (c)-[:MENTIONS]->(e)
            """,
            text=entity_text, type=entity_type,
            fir_number=fir_number, filename=filename, case_key=case_key
        )


def write_extractions_to_graph(case_id: str, filename: str, entities: list, regex_entities: dict = None):
    fir_number = regex_entities.get("fir_number") if regex_entities else None
    create_case_node(case_id, filename, fir_number)

    for ent in entities:
        create_entity_node(ent["text"], ent["type"], fir_number, filename)

    if regex_entities:
        for phone in regex_entities.get("phone_numbers", []):
            create_entity_node(phone, "phone_number", fir_number, filename)
        for vehicle in regex_entities.get("vehicle_numbers", []):
            create_entity_node(vehicle, "vehicle_number", fir_number, filename)


def resolve_entity_type(entity_text: str, entities: list, default: str = "unknown") -> str:
    entity_lower = entity_text.lower().strip()
    for ent in entities:
        if ent["text"].lower().strip() == entity_lower:
            return ent["type"]
    return default


def _create_relationship(tx, rel: dict, fir_number: str, filename: str, entities: list):
    subject_type = resolve_entity_type(rel["subject"], entities)
    object_type = resolve_entity_type(rel["object"], entities)
    case_key = fir_number or filename

    subject_key = (
        "{text: $subject, type: $subject_type}"
        if subject_type in GLOBAL_TYPES
        else "{text: $subject, type: $subject_type, case_key: $case_key}"
    )
    object_key = (
        "{text: $object, type: $object_type}"
        if object_type in GLOBAL_TYPES
        else "{text: $object, type: $object_type, case_key: $case_key}"
    )

    query = f"""
    MERGE (s:Entity {subject_key})
    MERGE (o:Entity {object_key})
    MERGE (s)-[r:RELATION {{type: $relation, fir: $fir_number}}]->(o)
    SET r.source_span = $source_span
    """
    tx.run(
        query,
        subject=rel["subject"], subject_type=subject_type,
        object=rel["object"], object_type=object_type,
        relation=rel["relation"], source_span=rel.get("source_span", ""),
        fir_number=fir_number, case_key=case_key,
    )


def write_relationships_to_graph(case_id: str, relationships: list, filename: str, entities: list, fir_number: str = None):
    with get_session() as session:
        for rel in relationships:
            session.execute_write(_create_relationship, rel, fir_number, filename, entities)