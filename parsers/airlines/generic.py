from parsers.base import BoardingPassParser
from parsers.dataclass import ParsedBoardingPass

class IATAGenericParser(BoardingPassParser):
    def __init__(self):
        super().__init__()
        
    def _can_handle(self, *args, **kwargs) -> bool:
        return True

    def _parse_content(self, raw_data: str, bp_obj: ParsedBoardingPass) -> ParsedBoardingPass:
        return bp_obj