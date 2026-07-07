from unittest.mock import patch, MagicMock
from backend.assistant.query_engine import query, filter_summary_entities


# --- filter_summary_entities ---

def test_filter_removes_noise_types():
    results = [
        {"text": "Vikram Reddy", "type": "person"},
        {"text": "42", "type": "number"},
        {"text": "Bengaluru", "type": "location"},
        {"text": "28/06/2026", "type": "date"},
        {"text": "KA03AB1122", "type": "vehicle_number"},
    ]
    filtered = filter_summary_entities(results)
    types = [r["type"] for r in filtered]
    assert "number" not in types
    assert "date" not in types
    assert "person" in types
    assert "location" in types
    assert "vehicle_number" in types

def test_filter_removes_pure_digits():
    results = [
        {"text": "31", "type": "person"},
        {"text": "Rohan Kumar", "type": "person"},
    ]
    filtered = filter_summary_entities(results)
    assert len(filtered) == 1
    assert filtered[0]["text"] == "Rohan Kumar"

def test_filter_empty_input():
    assert filter_summary_entities([]) == []


# --- query function ---

def make_groq_response(content: str):
    message = MagicMock()
    message.content = content
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    return response

def make_neo4j_session(records: list[dict]):
    session = MagicMock()
    session.__enter__ = MagicMock(return_value=session)
    session.__exit__ = MagicMock(return_value=False)
    session.run.return_value = [
        MagicMock(**{"__iter__": MagicMock(return_value=iter(r.items())),
                     "keys": MagicMock(return_value=list(r.keys())),
                     "data": MagicMock(return_value=r)})
        for r in records
    ]
    return session

@patch("backend.assistant.query_engine.get_session")
@patch("backend.assistant.query_engine.client")
def test_query_graph_query_type(mock_client, mock_session):
    mock_client.chat.completions.create.side_effect = [
        make_groq_response('{"type": "GRAPH_QUERY", "cypher": "MATCH (n) RETURN n.text LIMIT 1"}'),
        make_groq_response("Vikram Reddy is the accused person.")
    ]
    session = MagicMock()
    session.__enter__ = MagicMock(return_value=session)
    session.__exit__ = MagicMock(return_value=False)
    session.run.return_value = iter([])
    mock_session.return_value = session

    result = query("Who is the accused?")
    assert result["type"] == "GRAPH_QUERY"
    assert "cypher" in result
    assert "answer" in result

@patch("backend.assistant.query_engine.client")
def test_query_direct_answer_type(mock_client):
    mock_client.chat.completions.create.return_value = make_groq_response(
        '{"type": "DIRECT_ANSWER", "answer": "There are 3 FIRs in the system."}'
    )
    result = query("How many FIRs are there?")
    assert result["type"] == "DIRECT_ANSWER"
    assert "answer" in result

@patch("backend.assistant.query_engine.client")
def test_query_invalid_json_returns_error(mock_client):
    mock_client.chat.completions.create.return_value = make_groq_response(
        "This is not JSON at all"
    )
    result = query("Some question")
    assert result["type"] == "error"

@patch("backend.assistant.query_engine.get_session")
@patch("backend.assistant.query_engine.client")
def test_query_cypher_error_returns_error(mock_client, mock_session):
    mock_client.chat.completions.create.return_value = make_groq_response(
        '{"type": "GRAPH_QUERY", "cypher": "INVALID CYPHER"}'
    )
    session = MagicMock()
    session.__enter__ = MagicMock(return_value=session)
    session.__exit__ = MagicMock(return_value=False)
    session.run.side_effect = Exception("Cypher syntax error")
    mock_session.return_value = session

    result = query("Who is accused?")
    assert result["type"] == "error"