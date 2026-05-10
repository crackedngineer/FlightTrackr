import logging
from datetime import date, datetime, timezone
from celery import Task
from googleapiclient.errors import HttpError
from app.tasks.celery_app import celery_app
from app.db.session import SyncSessionLocal
from app.models.gmail_sync_job import GmailSyncJob
from app.services.mail_token_service import load_connection_sync
from app.mail.gmail import GmailProvider
from app.services.gmail_service import GmailService
from app.services.flight_service import (
    _parse_departure_to_datetime,
    get_airline_by_iata_sync,
    get_airport_by_iata_sync,
    get_existing_message_ids_sync,
    upsert_booking_sync,
    upsert_flight_sync,
    upsert_passenger_sync,
    upsert_boarding_pass_sync,
    update_booking_metadata_sync,
)
from app.services.parser_service import BoardingPassService
from app.parsers.factory import ParserFactory
from app.core.settings import get_settings

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    max_retries=3,
    autoretry_for=(HttpError,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
)
def sync_gmail_boarding_passes(self: Task, user_id: str, job_id: str) -> dict:
    settings = get_settings()

    with SyncSessionLocal() as session:
        job = session.get(GmailSyncJob, job_id)
        if not job:
            logger.error(f"GmailSyncJob {job_id} not found")
            return {"error": "job_not_found"}

        job.status = "running"
        job.started_at = datetime.now(timezone.utc)
        session.commit()

        try:
            creds = load_connection_sync(session, user_id, "gmail")
            if not creds.refresh_token:
                raise ValueError("No Gmail refresh token found — user must re-authenticate")

            gmail = GmailService(creds.refresh_token)

            message_ids = gmail.search_messages(
                query=settings.gmail_search_query,
                max_results=settings.gmail_max_results,
            )
            job.emails_scanned = len(message_ids)
            session.commit()

            if not message_ids:
                job.status = "completed"
                job.completed_at = datetime.now(timezone.utc)
                session.commit()
                return {"emails_scanned": 0, "passes_found": 0, "passes_saved": 0}

            existing_ids = get_existing_message_ids_sync(session, user_id, "gmail", message_ids)
            new_ids = [mid for mid in message_ids if mid not in existing_ids]

            parser_service = BoardingPassService(factory=ParserFactory())
            passes_found = 0
            passes_saved = 0

            for msg_id in new_ids:
                try:
                    attachments = gmail.get_pdf_attachments(msg_id)
                    for _filename, pdf_bytes in attachments:
                        try:
                            parsed = parser_service.process(pdf_bytes)
                            passes_found += 1

                            airline = get_airline_by_iata_sync(session, parsed.operator_code or "")
                            if not airline:
                                logger.warning(f"Unknown airline '{parsed.operator_code}', skipping")
                                continue

                            dep_airport = get_airport_by_iata_sync(session, parsed.origin or "")
                            arr_airport = get_airport_by_iata_sync(session, parsed.destination or "")
                            if not dep_airport or not arr_airport:
                                logger.warning(
                                    f"Unknown airport '{parsed.origin}'/'{parsed.destination}', skipping"
                                )
                                continue

                            departure_dt = _parse_departure_to_datetime(parsed.departure_time)
                            if not departure_dt:
                                logger.warning(f"Could not parse departure time '{parsed.departure_time}', skipping")
                                continue

                            flight_status = "upcoming" if departure_dt.date() >= date.today() else "completed"
                            flight_number = f"{(parsed.operator_code or '').strip()}{(parsed.flight_number or '').strip()}"

                            with session.begin_nested():
                                booking = upsert_booking_sync(
                                    session, user_id, airline.id,
                                    parsed.pnr_code or "", source="gmail",
                                )
                                flight = upsert_flight_sync(
                                    session, booking.id, airline.id,
                                    dep_airport.id, arr_airport.id,
                                    flight_number, departure_dt,
                                )
                                flight.status = flight_status
                                session.flush()

                                passenger = upsert_passenger_sync(
                                    session, booking.id,
                                    parsed.passenger_firstname, parsed.passenger_lastname,
                                )
                                upsert_boarding_pass_sync(
                                    session, flight.id, passenger.id,
                                    barcode=parsed.barcode or "",
                                    seat_number=parsed.seat_number,
                                    cabin_class=parsed.cabin_class,
                                    boarding_group=parsed.boarding_group,
                                    source="gmail",
                                    source_message_id=msg_id,
                                )
                                update_booking_metadata_sync(session, booking.id)

                            passes_saved += 1

                        except Exception as parse_err:
                            logger.warning(f"Failed to parse PDF from msg {msg_id}: {parse_err}")
                except Exception as msg_err:
                    logger.warning(f"Failed to fetch attachments for msg {msg_id}: {msg_err}")

            session.commit()

            job.passes_found = passes_found
            job.passes_saved = passes_saved
            job.status = "completed"
            job.completed_at = datetime.now(timezone.utc)
            session.commit()

            return {
                "emails_scanned": len(message_ids),
                "passes_found": passes_found,
                "passes_saved": passes_saved,
            }

        except Exception as exc:
            logger.exception(f"Gmail sync failed for user {user_id}: {exc}")
            job.status = "failed"
            job.error_message = str(exc)[:500]
            job.completed_at = datetime.now(timezone.utc)
            session.commit()
            raise
