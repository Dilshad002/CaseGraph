from backend.nlp.regex_extractor import extract_person_attributes, extract_incident_details


# --- extract_person_attributes ---
def test_extract_person_attributes_standard_format():
    text = (
        "Complainant Details\n"
        "Name: Rohan Kumar\n"
        "Age: 31\n"
        "Mobile: 9876543210\n"
        "\n"
        "Accused Details\n"
        "Name: Vikram Reddy\n"
        "Age: 34\n"
        "Mobile: 9123456789"
    )
    result = extract_person_attributes(text)
    names = [r["name"] for r in result]
    assert "Rohan Kumar" in names
    assert "Vikram Reddy" in names
    rohan = next(r for r in result if r["name"] == "Rohan Kumar")
    vikram = next(r for r in result if r["name"] == "Vikram Reddy")
    assert rohan["attributes"]["age"] == "31"
    assert vikram["attributes"]["age"] == "34"
    assert rohan["attributes"]["mobile"] == "9876543210"
    assert vikram["attributes"]["mobile"] == "9123456789"

def test_extract_person_attributes_abbreviated_header():
    text = """Complainant:
    Name: Anjali Mehta
    Age: 29

    Accused:
    Name: Vikram Reddy
    Age: 32"""
    result = extract_person_attributes(text)
    names = [r["name"] for r in result]
    assert "Anjali Mehta" in names
    assert "Vikram Reddy" in names
    vikram = next(r for r in result if r["name"] == "Vikram Reddy")
    assert vikram["attributes"]["age"] == "32"

def test_extract_person_attributes_no_age():
    text = """Accused:
    Name: Arjun Verma"""
    result = extract_person_attributes(text)
    assert result == [] or all("age" not in r["attributes"] for r in result)

def test_extract_person_attributes_no_duplicates():
    text = """Complainant Details
    Name: Rohan Kumar
    Age: 31

    Accused Details
    Name: Vikram Reddy
    Age: 34"""
    result = extract_person_attributes(text)
    names = [r["name"] for r in result]
    assert len(names) == len(set(names))

def test_extract_person_attributes_empty():
    assert extract_person_attributes("") == []


# --- extract_incident_details ---
def test_extract_incident_details_standard():
    text = """Date of Occurrence: 28/06/2026
    Time: Between 08:15 PM and 08:45 PM
    Place of Occurrence:
    Phoenix Marketcity Parking Area, Whitefield Main Road, Bengaluru.

    Description:"""
    result = extract_incident_details(text)
    assert result["date"] == "28/06/2026"
    assert result["time_start"] == "08:15 PM"
    assert result["time_end"] == "08:45 PM"
    assert "Phoenix Marketcity" in result["place"]

def test_extract_incident_details_single_time():
    text = """Date of Occurrence: 12/07/2026
    Time: 08:15 PM
    Place of Occurrence:
    100 Feet Road, Indiranagar, Bengaluru

    Incident:"""
    result = extract_incident_details(text)
    assert result["date"] == "12/07/2026"
    assert result["time_start"] == "08:15 PM"
    assert result["time_end"] is None

def test_extract_incident_details_missing_date():
    text = """Time: Between 08:15 PM and 08:45 PM
    Place of Occurrence: Some Location"""
    result = extract_incident_details(text)
    assert result["date"] is None

def test_extract_incident_details_missing_place():
    text = """Date of Occurrence: 28/06/2026
    Time: 08:15 PM"""
    result = extract_incident_details(text)
    assert result["place"] is None

def test_extract_incident_details_empty():
    result = extract_incident_details("")
    assert result["date"] is None
    assert result["time_start"] is None
    assert result["place"] is None
