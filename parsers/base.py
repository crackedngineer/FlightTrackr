from pathlib import Path
from abc import ABC, abstractmethod
import re
import numpy as np
from datetime import datetime
from PIL import Image
import zxingcpp
import pdfplumber
from parsers.dataclass import ParsedBoardingPass
from parsers.utils import extract_text_pdfplumber, is_pdf_valid, is_valid_bcbp

class BoardingPassParser(ABC):
    def __init__(self):
        self._raw_data = None
        self.bp_details = ParsedBoardingPass(operator_code=self.airline_code)

    @property
    def raw_data(self):
        if self._raw_data is None:
            self._raw_data = extract_text_pdfplumber(self.pdf_path)
        return self._raw_data
    
    @property
    def pdf_path(self): 
        return self._pdf_path
    
    @pdf_path.setter
    def pdf_path(self, value: Path):
        if value is None or not is_pdf_valid(value):
            raise ValueError("Invalid PDF: Either scanned or too short")
        self._pdf_path = value
    
    def can_handle(self) -> bool:
        return self._can_handle(self.raw_data)
    
    @abstractmethod
    def _can_handle(self, raw_data: str) -> bool:
        pass
    
    def decode_bcbp(self, image: Image.Image) -> list[str]:
        img_np = np.array(image)
        results = zxingcpp.read_barcodes(img_np)
        return [r.text.strip() for r in results if r.text]

    def extract_bcbp_barcode(self, pdf_path: Path) -> str:
        with pdfplumber.open(pdf_path) as pdf:
            for page_number, page in enumerate(pdf.pages, start=1):

                # 🔥 Render full page (IMPORTANT)
                pil_image = page.to_image(resolution=300).original

                decoded_list = self.decode_bcbp(pil_image)
                for data in decoded_list:
                    if is_valid_bcbp(data):
                        print(f"✅ Found on page {page_number}")
                        return data
        return ""
    
    def parse_bcbp(self, bcbp_data: str) -> None:
        result = {}
        name_bcbp = bcbp_data[2:22].replace(" ", "")
        fullname = name_bcbp.split("/")
        self.bp_details.passenger_firstname = str(re.sub('(MRS|MR|MS|MSTR|DR)$','',fullname[1]).replace(" ", ""))
        self.bp_details.passenger_lastname = str(fullname[0].replace(" ", ""))
        
        self.bp_details.pnr_code = str(bcbp_data[22:30].replace(" ", ""))
        self.bp_details.origin = str(bcbp_data[30:33].replace(" ", ""))
        self.bp_details.destination = str(bcbp_data[33:36].replace(" ", ""))
        self.bp_details.operator_code = str(bcbp_data[36:38].replace(" ", ""))
        self.bp_details.flight_number = str(bcbp_data[39:43].replace(" ", ""))
        self.bp_details.departure_time = str(datetime.strptime(bcbp_data[44:47], '%j').strftime('%d/%b'))
        self.bp_details.cabin_class = str(bcbp_data[47].replace(" ", ""))
        self.bp_details.seat_number = str(bcbp_data[48:52].replace(" ", ""))
        self.bp_details.checkin_sequence = str(bcbp_data[52:56].replace(" ", ""))
        
        return result

    def parse(self) -> ParsedBoardingPass:
        barcode_data = self.extract_bcbp_barcode(self._pdf_path)
        self.parse_bcbp(barcode_data)
        return self._parse_content(self.raw_data)
        
    @abstractmethod
    def _parse_content(self, content: str) -> ParsedBoardingPass:
        pass