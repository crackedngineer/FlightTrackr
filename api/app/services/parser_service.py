"""
Boarding pass parsing service with proper error handling.
Implements business logic for parsing boarding passes from PDF files.
"""

from app.parsers.dataclass import ParsedBoardingPass
from app.parsers.factory import ParserFactory
from app.parsers.bcbp_decoder import extract_bcbp_barcode, parse_bcbp_barcode
from app.parsers.utils import extract_text_pdfplumber
from app.core.exceptions import BoardingPassParsingException, ValidationException
import logging


class BoardingPassService:
    """Service for processing boarding pass documents."""

    def __init__(self, factory: ParserFactory):
        self.factory = factory
        self.logger = logging.getLogger(__name__)

    def process(self, pdf_bytes: bytes) -> ParsedBoardingPass:
        """
        Process boarding pass PDF and extract flight information.

        Args:
            pdf_bytes: PDF file content as bytes

        Returns:
            Parsed boarding pass data

        Raises:
            ValidationException: If input is invalid
            BoardingPassParsingException: If parsing fails
        """
        if not pdf_bytes:
            raise ValidationException("PDF content is empty")

        try:
            self.logger.info("Starting boarding pass parsing process")

            # Decode BCBP barcode and extract details
            bcbp_barcode = extract_bcbp_barcode(pdf_bytes)
            if not bcbp_barcode:
                raise BoardingPassParsingException(
                    "Invalid or missing BCBP barcode in boarding pass"
                )

            bcbp_details = parse_bcbp_barcode(bcbp_barcode)
            if not bcbp_details:
                raise BoardingPassParsingException("Failed to parse BCBP barcode data")

            # Extract text content from PDF
            raw_data = extract_text_pdfplumber(pdf_bytes)
            if not raw_data or not raw_data.strip():
                self.logger.error("No text content extracted from PDF")
                # raise BoardingPassParsingException(
                #     "Could not extract text content from PDF"
                # )

            # Get appropriate parser based on airline
            parser = self.factory.get_parser(
                bcbp_details.get("operator_code", None), raw_data
            )

            if not parser:
                raise BoardingPassParsingException(
                    "No suitable parser found for this boarding pass"
                )

            # Parse the boarding pass content
            result = parser.parse(raw_data, bcbp_details)

            if not result:
                raise BoardingPassParsingException(
                    "Parser failed to extract boarding pass data"
                )

            self.logger.info(
                f"Successfully parsed boarding pass for flight {result.flight_number}"
            )

            return result

        except (ValidationException, BoardingPassParsingException):
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            self.logger.error(
                f"Unexpected error during boarding pass processing: {str(e)}"
            )
            raise BoardingPassParsingException(
                f"Failed to process boarding pass: {str(e)}"
            )
