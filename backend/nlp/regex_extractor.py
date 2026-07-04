import re

PHONE_PATTERN = re.compile(r"(?:\+91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}")
VEHICLE_PATTERN = re.compile(r'\b[A-Z]{2}[\s\-]?\d{1,2}[\s\-]?[A-Z]{1,3}[\s\-]?\d{4}\b')
FIR_NUMBER_PATTERN = re.compile(
    r'\b(?:FIR\s*(?:No\.?|Number)?|Case\s*No\.?|Crime\s*No\.?)\s*:?\s*([A-Za-z0-9-]+(?:/[A-Za-z0-9-]+){1,3})\b',
    re.IGNORECASE
)

IMEI_PATTERN = re.compile(r'(?:IMEI)\s*:?\s*(\d{15})\b', re.IGNORECASE)
AADHAAR_PATTERN = re.compile(r'(?:Aadhaar|Aadhar)\s*:?\s*(\d{4}\s?\d{4}\s?\d{4})\b', re.IGNORECASE)
PAN_PATTERN = re.compile(r'\b([A-Z]{5}\d{4}[A-Z])\b')
IFSC_PATTERN = re.compile(r'\b([A-Z]{4}0[A-Z0-9]{6})\b')
PASSPORT_PATTERN = re.compile(r'(?:Passport\s*(?:No\.?|Number)?)\s*:?\s*([A-Z]\d{7})\b', re.IGNORECASE)
UPI_PATTERN = re.compile(r'\b([\w.\-]+@(?:okaxis|ybl|paytm|oksbi|okhdfcbank|okicici|okaxisp|apl|axl|ibl|sbi|hdfcbank))\b', re.IGNORECASE)
BANK_ACCOUNT_PATTERN = re.compile(r'(?:Bank\s*Account|Account\s*No\.?|A/C\s*No\.?)\s*(?:Mentioned)?:?\s*(\d{9,18})\b', re.IGNORECASE)
DRIVING_LICENCE_PATTERN = re.compile(r'(?:Driving\s*Licen[cs]e)\s*:?\s*([A-Z]{2}\d{13,14})\b', re.IGNORECASE)

AGE_PATTERN = re.compile(
    r'(?:Accused|Complainant)\s+Details.*?Age:\s*(\d+)',
    re.DOTALL | re.IGNORECASE
)
ADDRESS_PATTERN = re.compile(
    r'(?:Accused|Complainant)\s+Details.*?Address:\s*(.+?)(?:Mobile:|Email:|Aadhaar:|$)',
    re.DOTALL | re.IGNORECASE
)

def extract_description_section(text: str) -> str:
    match = re.search(r'Description:\s*(.+?)(?:Witnesses|Recovered Evidence|Investigating Officer|$)',
        text, re.DOTALL | re.IGNORECASE
    )
    return match.group(1).strip() if match else text

def extract_person_attributes(text: str, role_map: dict = None) -> list[dict]:
    results = []
    section_pattern = re.compile(r'(Complainant|Accused)\s+Details\s*[\r\n]+Name:\s*(.+?)[\r\n]+Age:\s*(\d+)',
    re.IGNORECASE
    )
    for match in section_pattern.finditer(text):
        name = match.group(2).strip()
        age = match.group(3).strip()
        results.append({"name": name, "attributes": {"age": age}})
    return results

def strip_overlapping_ner_entities(entities: list, regex_entities: dict) -> list:
    raw_values = set()
    digit_values = set()

    for key, values in regex_entities.items():
        if values is None:
            continue
        if isinstance(values, str):
            values = [values]
        for v in values:
            if not v:
                continue
            raw_values.add(v.strip())
            digits = re.sub(r'\D', '', v)
            if digits:
                digit_values.add(digits)

    filtered = []
    for ent in entities:
        text = ent["text"].strip()
        ent_digits = re.sub(r'\D', '', text)

        if text in raw_values:
            continue
        if ent_digits and ent_digits in digit_values:
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

def extract_imei_numbers(text: str) -> list[str]:
    return list(set(IMEI_PATTERN.findall(text)))


def extract_aadhaar_numbers(text: str) -> list[str]:
    matches = AADHAAR_PATTERN.findall(text)
    return list(set(re.sub(r'\s', '', m) for m in matches))


def extract_pan_numbers(text: str) -> list[str]:
    return list(set(PAN_PATTERN.findall(text)))


def extract_ifsc_codes(text: str) -> list[str]:
    return list(set(IFSC_PATTERN.findall(text)))


def extract_passport_numbers(text: str) -> list[str]:
    return list(set(PASSPORT_PATTERN.findall(text)))


def extract_upi_ids(text: str) -> list[str]:
    return list(set(UPI_PATTERN.findall(text)))


def extract_bank_accounts(text: str) -> list[str]:
    return list(set(BANK_ACCOUNT_PATTERN.findall(text)))


def extract_driving_licences(text: str) -> list[str]:
    return list(set(DRIVING_LICENCE_PATTERN.findall(text)))

def extract_regex_entities(text: str) -> dict:
    return {
        "phone_numbers": extract_phone_numbers(text),
        "vehicle_numbers": extract_vehicle_numbers(text), 
        "fir_number": extract_fir_number(text),
         "imei_numbers": extract_imei_numbers(text),
        "aadhaar_numbers": extract_aadhaar_numbers(text),
        "pan_numbers": extract_pan_numbers(text),
        "ifsc_codes": extract_ifsc_codes(text),
        "passport_numbers": extract_passport_numbers(text),
        "upi_ids": extract_upi_ids(text),
        "bank_accounts": extract_bank_accounts(text),
        "driving_licences": extract_driving_licences(text)
    }