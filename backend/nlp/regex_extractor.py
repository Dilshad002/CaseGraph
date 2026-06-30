import re

PHONE_PATTERN = re.compile(r"(?:\+91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}")
VEHICLE_PATTERN = re.compile(r'\b[A-Z]{2}[\s\-]?\d{1,2}[\s\-]?[A-Z]{1,3}[\s\-]?\d{4}\b')
FIR_NUMBER_PATTERN = re.compile(
    r'\b(?:FIR\s*(?:No\.?|Number)?|Case\s*No\.?|Crime\s*No\.?)\s*:?\s*([A-Za-z0-9-]+(?:/[A-Za-z0-9-]+){1,3})\b',
    re.IGNORECASE
)

def strip_overlapping_ner_entities(entities: list, regex_entities: dict) -> list:
    phone_digits = set(regex_entities.get("phone_numbers", []))
    vehicle_numbers = set(regex_entities.get("vehicle_numbers", []))

    filtered = []
    for ent in entities:
        ent_digits = re.sub(r'\D', '', ent["text"])
        if ent_digits in phone_digits:
            continue
        if ent["text"].strip() in vehicle_numbers:
            continue
        filtered.append(ent)
    return filtered

def extract_fir_number(text: str) -> str | None:
    match = FIR_NUMBER_PATTERN.search(text)
    return match.group(1) if match else None

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

def extract_regex_entities(text: str) -> dict:
    return {
        "phone_numbers": extract_phone_numbers(text),
        "vehicle_numbers": extract_vehicle_numbers(text), 
        "fir_number": extract_fir_number(text)
    }