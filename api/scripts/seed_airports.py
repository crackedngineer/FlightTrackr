import csv
import io
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import httpx
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db.session import SyncSessionLocal
from app.models.airport import Airport

SOURCE_URL = "https://davidmegginson.github.io/ourairports-data/airports.csv"


def _transform(row: dict, seen_icao: set[str]) -> dict | None:
    if row.get("type") != "large_airport":
        return None

    iata = row.get("iata_code", "").strip()
    name = row.get("name", "").strip()
    if not iata or not name:
        return None

    icao = row.get("icao_code", "").strip() or None
    if icao in seen_icao:
        icao = None
    elif icao:
        seen_icao.add(icao)

    lat_raw = row.get("latitude_deg", "").strip()
    lon_raw = row.get("longitude_deg", "").strip()

    return {
        "iata_code": iata,
        "icao_code": icao,
        "name": name,
        "city": row.get("municipality", "").strip() or None,
        "country": row.get("iso_country", "").strip() or None,
        "latitude": float(lat_raw) if lat_raw else None,
        "longitude": float(lon_raw) if lon_raw else None,
        "timezone": None,
    }


def seed() -> None:
    print(f"Fetching {SOURCE_URL} …")
    resp = httpx.get(SOURCE_URL, follow_redirects=True, timeout=60)
    resp.raise_for_status()

    reader = csv.DictReader(io.StringIO(resp.text))
    seen_icao: set[str] = set()
    rows: list[dict] = []
    total_read = 0

    for row in reader:
        total_read += 1
        transformed = _transform(row, seen_icao)
        if transformed:
            rows.append(transformed)

    print(f"  {total_read} records read, {len(rows)} large airports")

    if not rows:
        print("No rows to insert.")
        return

    with SyncSessionLocal() as session:
        stmt = (
            pg_insert(Airport)
            .values(rows)
            .on_conflict_do_update(
                index_elements=["icao_code"],
                set_={
                    "name":      pg_insert(Airport).excluded.name,
                    "icao_code": pg_insert(Airport).excluded.icao_code,
                    "city":      pg_insert(Airport).excluded.city,
                    "country":   pg_insert(Airport).excluded.country,
                    "latitude":  pg_insert(Airport).excluded.latitude,
                    "longitude": pg_insert(Airport).excluded.longitude,
                },
            )
        )
        session.execute(stmt)
        session.commit()
        total = session.query(Airport).count()

    print(f"Done — {len(rows)} upserted, {total} total rows in airports table.")


if __name__ == "__main__":
    seed()
