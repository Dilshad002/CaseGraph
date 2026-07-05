import re
import unicodedata

def clean_text(text: str) -> str:
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    # Remove zero-width and invisible Unicode characters
    text = ''.join(c for c in text if not unicodedata.category(c).startswith('C') or c in '\n\t')
    # Remove leading whitespace from each line 
    text = '\n'.join(line.strip() for line in text.split('\n'))
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]+', '', text)
    return text.strip()
