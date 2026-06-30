import pytesseract
from PIL import Image
import io

def extract_text_from_image(image_bytes: bytes)-> str:
    image = Image.open(io.BytesIO(image_bytes)) #convert bytes to image
    text = pytesseract.image_to_string(image, config='--psm 6')
    
    return text.strip()
