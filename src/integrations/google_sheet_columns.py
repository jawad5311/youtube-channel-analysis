"""Load and refresh the configured Google Sheet column order."""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from googleapiclient.discovery import build

from src.integrations.google_sheets_auth import authorize

DEFAULT_COLUMNS_PATH = Path(__file__).resolve().parents[2] / "config" / "google-sheet-columns.txt"
DEFAULT_CACHE_PATH = Path(__file__).resolve().parents[2] / "config" / "google-sheet-columns-cache.json"
DEFAULT_SHEET_URL_PATH = Path(__file__).resolve().parents[2] / "config" / "google-sheet-url.txt"
CACHE_TTL = timedelta(hours=24)


def spreadsheet_id_from_url(path: Path = DEFAULT_SHEET_URL_PATH) -> str:
    """Read a Google Sheets URL and return its spreadsheet ID."""
    value = path.expanduser().resolve().read_text(encoding="utf-8-sig").strip()
    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", value)
    if not match:
        raise ValueError(f"Invalid Google Sheets URL in {path}")
    return match.group(1)


def spreadsheet_column_name(index: int) -> str:
    """Return the spreadsheet column label for a zero-based index."""
    if index < 0:
        raise ValueError("Column index must be nonnegative.")
    label = ""
    number = index + 1
    while number:
        number, remainder = divmod(number - 1, 26)
        label = chr(65 + remainder) + label
    return label


def load_columns(path: Path = DEFAULT_COLUMNS_PATH) -> list[dict[str, object]]:
    """Load one column name per line in its configured order."""
    path = path.expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Google Sheet columns file not found: {path}")
    return map_headers(path.read_text(encoding="utf-8-sig").splitlines())


def map_headers(headers: list[object]) -> list[dict[str, object]]:
    """Map non-empty headers to their original sheet positions."""
    columns = [(index, str(value).strip()) for index, value in enumerate(headers)
               if value is not None and str(value).strip()]
    if not columns:
        raise ValueError("No Google Sheet column names found.")
    normalized = [name.casefold() for _, name in columns]
    if len(normalized) != len(set(normalized)):
        raise ValueError("Google Sheet columns must be unique.")
    return [
        {"name": name, "index": index, "letter": spreadsheet_column_name(index)}
        for index, name in columns
    ]


def sheet_range(sheet_name: str, cells: str) -> str:
    """Build an A1 range for a sheet title, escaping apostrophes."""
    return "'" + sheet_name.replace("'", "''") + "'!" + cells


def read_column_cache(cache_path: Path = DEFAULT_CACHE_PATH) -> dict:
    try:
        cache = json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return cache if isinstance(cache, dict) else {}


def refresh_columns(
    spreadsheet_id: str,
    sheet_name: str,
    columns_path: Path = DEFAULT_COLUMNS_PATH,
    cache_path: Path = DEFAULT_CACHE_PATH,
) -> list[dict[str, object]]:
    """Read the sheet's first row and update the local column configuration."""
    credentials = authorize()
    service = build("sheets", "v4", credentials=credentials, cache_discovery=False)
    response = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=sheet_range(sheet_name, "1:1"))
        .execute()
    )
    values = response.get("values", [])
    return save_columns(spreadsheet_id, sheet_name, values[0] if values else [],
                        columns_path, cache_path)


def save_columns(
    spreadsheet_id: str,
    sheet_name: str,
    headers: list[object],
    columns_path: Path,
    cache_path: Path,
) -> list[dict[str, object]]:
    columns = map_headers(headers)
    names = ["" if value is None else str(value).strip() for value in headers]
    if any(len(name.splitlines()) > 1 for name in names):
        raise ValueError("Google Sheet headers must fit on one line each.")
    columns_path.parent.mkdir(parents=True, exist_ok=True)
    contents = "\n".join(names) + "\n"
    if not columns_path.is_file() or columns_path.read_text(encoding="utf-8-sig") != contents:
        columns_path.write_text(contents, encoding="utf-8")
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(
        json.dumps(
            {
                "spreadsheet_id": spreadsheet_id,
                "sheet_name": sheet_name,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return columns


def load_or_refresh_columns(
    spreadsheet_id: str,
    sheet_name: str,
    force: bool = False,
    columns_path: Path = DEFAULT_COLUMNS_PATH,
    cache_path: Path = DEFAULT_CACHE_PATH,
    *,
    headers: list[object] | None = None,
) -> list[dict[str, object]]:
    """Use the local mapping for 24 hours, then refresh it from Google Sheets."""
    if not force and cache_path.is_file() and columns_path.is_file():
        try:
            cache = read_column_cache(cache_path)
            fetched_at = datetime.fromisoformat(cache["fetched_at"])
            is_current = (
                cache["spreadsheet_id"] == spreadsheet_id
                and cache["sheet_name"] == sheet_name
                and timedelta(0) <= datetime.now(timezone.utc) - fetched_at < CACHE_TTL
            )
            if is_current:
                return load_columns(columns_path)
        except (OSError, KeyError, TypeError, ValueError):
            pass
    if headers is not None:
        return save_columns(spreadsheet_id, sheet_name, headers, columns_path, cache_path)
    return refresh_columns(spreadsheet_id, sheet_name, columns_path, cache_path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh cached Google Sheet column names.")
    parser.add_argument("--spreadsheet-id")
    parser.add_argument("--sheet-name")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    spreadsheet_id = args.spreadsheet_id or spreadsheet_id_from_url()
    sheet_name = args.sheet_name or cached_sheet_name(spreadsheet_id)
    if not sheet_name:
        parser.error("Provide --sheet-name when the spreadsheet has no cached tab.")
    columns = load_or_refresh_columns(spreadsheet_id, sheet_name, force=args.force)
    print(f"Loaded {len(columns)} columns.")
    print(", ".join(str(column["name"]) for column in columns))
    return 0


def cached_sheet_name(spreadsheet_id: str) -> str | None:
    cache = read_column_cache()
    if cache.get("spreadsheet_id") == spreadsheet_id:
        return cache.get("sheet_name")
    return None


if __name__ == "__main__":
    raise SystemExit(main())
