import re

FIELD_LABELS = [
    "FIR No", "FIR Number", "Case No", "Crime No",
    "State", "District", "Police Station",
    "Date of Registration", "Time of Registration",
    "Sections of Law", "BNS Sections",
    "Name", "Age", "Gender", "Address", "Mobile", "Phone", "Email",
    "Aadhaar", "Aadhar", "PAN", "IFSC", "UPI ID",
    "Driving Licence", "Driving License",
    "Date of Occurrence", "Time", "Place of Occurrence", "Description",
    "Registration No",
    "IMEI", "Bank Account Mentioned", "Bank Account",
    "Passport Number", "Passport No",
    "Investigating Officer", "Badge No",
    "Case Status",
]

_FIELD_LABELS_SORTED = sorted(FIELD_LABELS, key=len, reverse=True)
_LABEL_PATTERN = re.compile(
    r'\b(?:' + '|'.join(re.escape(l) for l in _FIELD_LABELS_SORTED) + r')\s*:?',
    re.IGNORECASE
)


def strip_field_labels(text: str) -> str:
    stripped = _LABEL_PATTERN.sub('.', text)
    stripped = re.sub(r'[ \t]+', ' ', stripped)
    stripped = re.sub(r'\n{3,}', '\n\n', stripped)
    stripped = re.sub(r'\.\s*\.', '.', stripped)  # collapse doubled periods
    return stripped.strip()