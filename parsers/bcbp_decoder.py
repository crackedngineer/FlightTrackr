import re
import pdfplumber
from io import BytesIO
from datetime import datetime

from parsers.utils import decode_bcbp, is_valid_bcbp

def extract_bcbp_barcode(pdf_bytes: bytes) -> str:
    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):

            # 🔥 Step 1: Try medium resolution first (faster)
            pil_image = page.to_image(resolution=200).original
            decoded_list = decode_bcbp(pil_image)

            for data in decoded_list:
                if is_valid_bcbp(data):
                    print(f"✅ Found on page {page_number} (200 DPI)")
                    return data

            # 🔁 Step 2: Retry with higher resolution only if needed
            pil_image = page.to_image(resolution=300).original
            decoded_list = decode_bcbp(pil_image)

            for data in decoded_list:
                if is_valid_bcbp(data):
                    print(f"✅ Found on page {page_number} (300 DPI)")
                    return data
    return ""


def parse_bcbp_barcode(bcbp_data: str) -> dict:
    result = {}

    name_bcbp = bcbp_data[2:22].replace(" ", "")
    fullname = name_bcbp.split("/")
    result["passenger_firstname"] = str(
        re.sub("(MRS|MR|MS|MSTR|DR)$", "", fullname[1]).replace(" ", "")
    )
    result["passenger_lastname"] = str(fullname[0].replace(" ", ""))

    result["pnr_code"] = str(bcbp_data[22:30].replace(" ", ""))
    result["origin"] = str(bcbp_data[30:33].replace(" ", ""))
    result["destination"] = str(bcbp_data[33:36].replace(" ", ""))
    result["operator_code"] = str(bcbp_data[36:38].replace(" ", ""))
    result["flight_number"] = str(bcbp_data[39:43].replace(" ", ""))
    result["departure_time"] = str(
        datetime.strptime(bcbp_data[44:47], "%j").strftime("%d/%b")
    )
    result["cabin_class"] = str(bcbp_data[47].replace(" ", ""))
    result["seat_number"] = str(bcbp_data[48:52].replace(" ", ""))
    result["checkin_sequence"] = str(bcbp_data[52:56].replace(" ", ""))

    return result