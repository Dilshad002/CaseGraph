import re

PHONE_PATTERN = re.compile(r"(?:\+91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}")
VEHICLE_PATTERN = re.compile(r'\b[A-Z]{2}[\s\-]?\d{1,2}[\s\-]?[A-Z]{1,3}[\s\-]?\d{4}\b')

def extract_phone_numbers(text: str) -> list:
    matches = PHONE_PATTERN.findall(text)
    cleaned = []
    for m in matches:
        digits = re.sub(r'\D', '', m)
        if digits.startswith('91') and len(digits) == 12:
            digits = digits[2:]
        if len(digits) == 10:
            cleaned.append(digits)
    return list(set(cleaned))

def extract_vehicle_numbers(text: str) -> list:
    matches = VEHICLE_PATTERN.findall(text)
    return list(set(m.strip() for m in matches))

def extract_entities(text: str) -> dict:
    return {
        "phone_numbers": extract_phone_numbers(text),
        "vehicle_numbers": extract_vehicle_numbers(text)
    }