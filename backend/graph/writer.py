from backend.graph.connection import get_session

def create_case_node(case_id: str, filename: str):
    with get_session() as session:
        session.run(
            """MERGE (c:Case {id: $case_id})
               SET c.filename = $filename
             """,
            case_id=case_id,
            filename=filename
        )

def create_entity_node(entity_text: str, entity_type: str, case_id: str):
    with get_session() as session:
        session.run(
            """MERGE (e:Entity {text: $text, type: $type})
               WITH e
               MATCH (c:Case {id: $case_id})
               MERGE (c)-[:MENTIONS]->(e)
             """,
            text=entity_text,
            type=entity_type,
            case_id=case_id
        )
def write_extractions_to_graph(case_id: str, filename: str, entities: list[dict]):
    create_case_node(case_id, filename)
    for ent in entities:
        create_entity_node(ent['text'], ent['type'], case_id)