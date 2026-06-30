import pytest
from backend.nlp.ner import extract_entities
from backend.nlp.regex_extractor import extract_phone_numbers, extract_vehicle_numbers, extract_fir_number


def test_extract_entities_finds_person():
    text = "Rahul Sharma visited the police station yesterday."
    entities = extract_entities(text)
    person_texts = [e["text"] for e in entities if e["type"] == "person"]
    assert "Rahul Sharma" in person_texts


def test_extract_entities_finds_location():
    text = "The accused fled towards Bengaluru."
    entities = extract_entities(text)
    location_texts = [e["text"] for e in entities if e["type"] == "location"]
    assert "Bengaluru" in location_texts


def test_extract_entities_empty_text():
    entities = extract_entities("")
    assert entities == []


def test_extract_phone_numbers_with_country_code():
    text = "Contact: +91 98765 43210"
    phones = extract_phone_numbers(text)
    assert "9876543210" in phones


def test_extract_phone_numbers_without_country_code():
    text = "Call me at 9876543210"
    phones = extract_phone_numbers(text)
    assert "9876543210" in phones


def test_extract_phone_numbers_no_match():
    text = "There is no phone number here."
    phones = extract_phone_numbers(text)
    assert phones == []


def test_extract_vehicle_numbers_no_hyphen():
    text = "The vehicle KA01AB1234 was seen near the location."
    vehicles = extract_vehicle_numbers(text)
    assert "KA01AB1234" in vehicles


def test_extract_vehicle_numbers_with_hyphen():
    text = "Another car KA-05-MN-9876 was also reported."
    vehicles = extract_vehicle_numbers(text)
    assert "KA-05-MN-9876" in vehicles


def test_extract_vehicle_numbers_no_match():
    text = "No vehicle mentioned in this sentence."
    vehicles = extract_vehicle_numbers(text)
    assert vehicles == []

def test_extract_fir_number_standard_format():
    text = "Case No: 145/2026"
    assert extract_fir_number(text) == "145/2026"

def test_extract_fir_number_no_match():
    text = "No FIR number mentioned here."
    assert extract_fir_number(text) is None

def test_extract_fir_number_standard():
    assert extract_fir_number("FIR No: 145/2026") == "145/2026"

def test_extract_fir_number_with_station_code():
    assert extract_fir_number("FIR Number: 0123/145/2026") == "0123/145/2026"

def test_extract_fir_number_crime_no_variant():
    assert extract_fir_number("Crime No. 45/2026") == "45/2026"

def test_extract_fir_number_not_confused_by_trailing_date():
    assert extract_fir_number("Case No: 145/2026, filed on 15/06/2026") == "145/2026"

def test_extract_fir_number_no_match():
    assert extract_fir_number("No FIR number mentioned here.") is None