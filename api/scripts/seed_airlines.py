import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import httpx
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db.session import SyncSessionLocal
from app.models.airline import Airline

SOURCE_URL = "https://raw.githubusercontent.com/npow/airline-codes/refs/heads/master/airlines.json"

DUPLICATE_ICAO_CODES = set()


def _transform(row: dict) -> dict | None:
    iata = row.get("iata", "").strip()
    icao = row.get("icao", "").strip()
    name = row.get("name", "").strip()
    active = row.get("active", "N") == "Y"
    if not iata or not name or not active or not icao or icao in DUPLICATE_ICAO_CODES:
        return None
    DUPLICATE_ICAO_CODES.add(iata)
    return {
        # "id":        int(row["id"]),
        "name": name,
        "alias": row.get("alias", "").strip() or None,
        "iata_code": iata,
        "icao_code": icao,
        "callsign": row.get("callsign", "").strip() or None,
        "country": row.get("country", "").strip() or None,
        "active": active,
    }


def seed() -> None:
    print(f"Fetching {SOURCE_URL} …")
    resp = httpx.get(SOURCE_URL, follow_redirects=True, timeout=30)
    resp.raise_for_status()
    raw: list[dict] = [
        *resp.json(),
        {
            "name": "Akasa Air",
            "iata_code": "QP",
            "icao_code": "AKJ",
            "callsign": "AKASA AIR",
            "country": "India",
            "active": True,
        },
    ]

    rows = [r for row in raw if (r := _transform(row)) is not None]
    print(f"  {len(raw)} records fetched, {len(rows)} valid (non-empty IATA)")

    with SyncSessionLocal() as session:
        stmt = (
            pg_insert(Airline)
            .values(rows[1:])
            .on_conflict_do_update(
                index_elements=["icao_code"],
                set_={
                    "name": pg_insert(Airline).excluded.name,
                    "alias": pg_insert(Airline).excluded.alias,
                    "icao_code": pg_insert(Airline).excluded.icao_code,
                    "callsign": pg_insert(Airline).excluded.callsign,
                    "country": pg_insert(Airline).excluded.country,
                    "active": pg_insert(Airline).excluded.active,
                },
            )
        )
        session.execute(stmt)
        session.commit()
        total = session.query(Airline).count()

    print(f"Done — {len(rows)} upserted, {total} total rows in airlines table.")


if __name__ == "__main__":
    seed()
