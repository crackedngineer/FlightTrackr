from parsers.base import BoardingPassParser
from parsers.dataclass import ParsedBoardingPass

class AkasaParser(BoardingPassParser):
    airline_code = "AI"
    def __init__(self):
        super().__init__()
        
    def _can_handle(self, raw_data: str) -> bool:
        return True
    
    def _parse_content(self, raw_data: str, bp_obj: ParsedBoardingPass) -> ParsedBoardingPass:
        bp_obj.operator_code = self.airline_code
        return bp_obj