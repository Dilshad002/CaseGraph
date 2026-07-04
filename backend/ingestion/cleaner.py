import re

def clean_text(text: str) -> str:
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]+', '', text)
    return text.strip()
