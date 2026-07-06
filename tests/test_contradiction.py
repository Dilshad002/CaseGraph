from unittest.mock import patch, MagicMock
from backend.reasoning.contradiction_detection import (detect_attribute_contradictions,
    detect_temporal_spatial_contradictions,
    times_overlap,
    parse_time
)


# --- Unit tests for time helpers ---

def test_times_overlap_clear_overlap():
    assert times_overlap("08:15 PM", "08:45 PM", "08:20 PM", "08:40 PM") is True

def test_times_overlap_no_overlap():
    assert times_overlap("08:00 PM", "08:30 PM", "09:00 PM", "09:30 PM") is False

def test_times_overlap_edge_touch():
    assert times_overlap("08:00 PM", "08:30 PM", "08:30 PM", "09:00 PM") is True

def test_times_overlap_missing_end():
    assert times_overlap("08:25 PM", None, "08:20 PM", "08:40 PM") is True

def test_parse_time_valid():
    t = parse_time("08:15 PM")
    assert t is not None
    assert t.hour == 20
    assert t.minute == 15

def test_parse_time_invalid():
    assert parse_time("not a time") is None

def test_parse_time_none():
    assert parse_time(None) is None


# --- Integration tests with mocked Neo4j ---

def make_mock_record(data: dict):
    record = MagicMock()
    record.keys.return_value = list(data.keys())
    record.__getitem__ = lambda self, key: data[key]
    record.data.return_value = data
    def mock_get(key, default=None):
        return data.get(key, default)
    record.get = mock_get
    return record

@patch("backend.reasoning.contradiction_detection.get_session")
def test_detect_attribute_contradiction_age(mock_session):
    mock_result = [
        {"attribute": "age", "value": "34", "fir_number": "145/2026"},
        {"attribute": "age", "value": "32", "fir_number": "152/2026"},
    ]
    session = MagicMock()
    session.__enter__ = MagicMock(return_value=session)
    session.__exit__ = MagicMock(return_value=False)
    session.run.return_value = [make_mock_record(r) for r in mock_result]
    mock_session.return_value = session

    result = detect_attribute_contradictions("Vikram Reddy")
    assert len(result) == 1
    assert result[0]["attribute"] == "age"
    assert "145/2026" in result[0]["conflict"]
    assert "152/2026" in result[0]["conflict"]
    assert result[0]["conflict"]["145/2026"] != result[0]["conflict"]["152/2026"]

@patch("backend.reasoning.contradiction_detection.get_session")
def test_detect_attribute_no_contradiction(mock_session):
    mock_result = [
        {"attribute": "age", "value": "34", "fir_number": "145/2026"},
        {"attribute": "age", "value": "34", "fir_number": "152/2026"},
    ]
    session = MagicMock()
    session.__enter__ = MagicMock(return_value=session)
    session.__exit__ = MagicMock(return_value=False)
    session.run.return_value = [make_mock_record(r) for r in mock_result]
    mock_session.return_value = session

    result = detect_attribute_contradictions("Vikram Reddy")
    assert result == []

@patch("backend.reasoning.contradiction_detection.get_session")
def test_detect_temporal_spatial_contradiction(mock_session):
    mock_result = [{
        "fir1": "145/2026",
        "location1": "Phoenix Marketcity Parking Area",
        "start1": "08:15 PM",
        "end1": "08:45 PM",
        "fir2": "152/2026",
        "location2": "100 Feet Road, Indiranagar",
        "start2": "08:20 PM",
        "end2": "08:40 PM",
        "date": "28/06/2026"
    }]
    session = MagicMock()
    session.__enter__ = MagicMock(return_value=session)
    session.__exit__ = MagicMock(return_value=False)
    session.run.return_value = [make_mock_record(r) for r in mock_result]
    mock_session.return_value = session

    result = detect_temporal_spatial_contradictions("Vikram Reddy")
    assert len(result) == 1
    assert result[0]["type"] == "temporal_spatial_conflict"
    assert "145/2026" in result[0]["conflict"]
    assert "152/2026" in result[0]["conflict"]

@patch("backend.reasoning.contradiction_detection.get_session")
def test_detect_temporal_no_overlap(mock_session):
    mock_result = [{
        "fir1": "145/2026",
        "location1": "Phoenix Marketcity",
        "start1": "08:00 PM",
        "end1": "08:30 PM",
        "fir2": "152/2026",
        "location2": "Indiranagar",
        "start2": "09:00 PM",
        "end2": "09:30 PM",
        "date": "28/06/2026"
    }]
    session = MagicMock()
    session.__enter__ = MagicMock(return_value=session)
    session.__exit__ = MagicMock(return_value=False)
    session.run.return_value = [make_mock_record(r) for r in mock_result]
    mock_session.return_value = session

    result = detect_temporal_spatial_contradictions("Vikram Reddy")
    assert result == []