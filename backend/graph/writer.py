from backend.graph.connection import get_session

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

        session.run(
            f"""
            MERGE (e:Entity {{text: $text, type: $type}})
            WITH e
            {match_clause}
            MERGE (c)-[:MENTIONS]->(e)
            """,
            text=entity_text, type=entity_type, fir_number=fir_number, filename=filename
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