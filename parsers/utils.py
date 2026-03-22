import zxingcpp
import pdfplumber
import numpy as np
from PIL import Image
from io import BytesIO


def is_valid_bcbp(data: str) -> bool:
    if not data.startswith("M1") or len(data) < 60:
        return False
    return True

def extract_text_pdfplumber(pdf_bytes: bytes) -> str:
    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)

def decode_bcbp(image: Image.Image) -> list[str]:
    img_np = np.array(image)
    results = zxingcpp.read_barcodes(img_np)
    return [r.text.strip() for r in results if r.text]