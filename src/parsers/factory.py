from parsers.base import BoardingPassParser
from parsers.airlines.akasa import AkasaParser
from parsers.airlines.indigo import IndigoParser
from parsers.airlines.generic import IATAGenericParser
from parsers.enum import AirlineCodeEnum

class ParserFactory:
    def __init__(self):
        self.parsers = {
            AirlineCodeEnum.INDIGO.value: IndigoParser,
            AirlineCodeEnum.AKASA_AIR.value: AkasaParser,
        }

    def get_parser(self, operator_code: str | None, raw_data: str) -> BoardingPassParser:
        if operator_code:
            parser_cls = self.parsers.get(operator_code)
            if parser_cls:
                return parser_cls()
        else:
            for parser in self.parsers.values():
                instance = parser()
                if instance.can_handle(raw_data):
                    return instance
        return IATAGenericParser()