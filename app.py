# from fastapi import FastAPI

# app = FastAPI(
#     title="Digipin Pro API",
#     version="1.0.0",
#     description="API for encoding/decoding DIGIPINs using the digipin-python library.",
# )

# @app.get("/", include_in_schema=False)
# async def root():
#     return {"message": "Welcome to the Boarding Pass Parser API. Go to /docs for API documentation."}

from pathlib import Path
from argparse import ArgumentParser

from parsers.dataclass import ParsedBoardingPass
from parsers.factory import ParserFactory
from parsers.bcbp_decoder import extract_bcbp_barcode, parse_bcbp_barcode
from parsers.utils import extract_text_pdfplumber


class BoardingPassService:

    def __init__(self, factory: ParserFactory):
        self.factory = factory

    def process(self, pdf_bytes: bytes) -> ParsedBoardingPass:
        # Decode BCBP barcode and extract details
        bcbp_barcode = extract_bcbp_barcode(pdf_bytes)
        if not bcbp_barcode:
            raise ValueError("Invalid or missing BCBP barcode")

        bcbp_details = parse_bcbp_barcode(bcbp_barcode)

        raw_data = extract_text_pdfplumber(pdf_bytes)
        parser = self.factory.get_parser(
            bcbp_details.get("operator_code", None), raw_data
        )
        result = parser.parse(raw_data, bcbp_details)
        return result


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument(
        "-f", "--file", help="Path to the boarding pass PDF file", required=True
    )
    args = parser.parse_args()

    factory = ParserFactory()
    service = BoardingPassService(factory)

    PDF_FILE = args.file
    with open(PDF_FILE, "rb") as f:
        pdf_bytes = f.read()
    parsed = service.process(pdf_bytes=pdf_bytes)
    print(parsed)
