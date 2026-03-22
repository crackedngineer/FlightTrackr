from abc import ABC, abstractmethod
from parsers.dataclass import ParsedBoardingPass
from parsers.utils import extract_text_pdfplumber

class BoardingPassParser(ABC):
    airline_code: str
    
    def can_handle(self, raw_data: str) -> bool:
        return self._can_handle(raw_data)
    
    @abstractmethod
    def _can_handle(self, raw_data: str) -> bool:
        pass

    def parse(self, raw_data: str, bcbp_details: dict) -> ParsedBoardingPass:
        bp_obj = ParsedBoardingPass(**bcbp_details)
        return self._parse_content(raw_data, bp_obj)
        
    @abstractmethod
    def _parse_content(self, raw_data: str, bp_obj: ParsedBoardingPass) -> ParsedBoardingPass:
        pass