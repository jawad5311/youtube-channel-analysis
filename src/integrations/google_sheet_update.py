"""Write the latest channel analysis into matching Google Sheet rows."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from googleapiclient.discovery import build

from src.integrations.google_sheet_columns import (
    DEFAULT_COLUMNS_PATH,
    DEFAULT_SHEET_URL_PATH,
    cached_sheet_name,
    load_or_refresh_columns,
    map_headers,
    sheet_range,
    spreadsheet_id_from_url,
)
from src.integrations.google_sheets_auth import authorize

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNS_ROOT = PROJECT_ROOT / "runs"
COUNTRIES = {
    "AU": "Australia", "CA": "Canada", "DK": "Denmark", "DE": "Germany",
    "IN": "India", "NZ": "New Zealand", "PK": "Pakistan", "GB": "United Kingdom",
    "US": "United States",
}
ANALYSIS_OUTPUTS = {
    "Channel Category": Path("channel-categorization-output.md"),
    "Niche": Path("channel-niche-search-output.md"),
    "Issues": Path("channel-issues/channel-issues-orchestrator-output.md"),
}
NO_CHANNEL_ISSUES = "no channel issues found after analysis"


def write_export_status(run_dir: Path, status: str, rows_updated: int | None = None) -> None:
    """Persist whether this run reached the sheet, without storing credentials."""
    payload = {"status": status, "rows_updated": rows_updated,
               "checked_at": datetime.now(timezone.utc).isoformat()}
    path = run_dir / "sheet-export-status.json"
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def sheet_channel_link(value: str) -> str:
    """Return a YouTube channel link in the sheet's preferred format."""
    value = value.strip()
    parsed = urlsplit(value if "://" in value else "//" + value)
    if parsed.hostname in {"youtube.com", "www.youtube.com", "m.youtube.com"}:
        path = parsed.path.rstrip("/")
        if path.startswith("/@") and len(path) > 2:
            return "youtube.com/" + path.split("/")[1]
        if path:
            return "youtube.com" + path
    return value.rstrip("/")


def read_completed_outputs(run_dir: Path) -> dict[str, str]:
    """Read the workflow's final outputs, rejecting missing or empty placeholders."""
    results = {}
    for name, relative_path in ANALYSIS_OUTPUTS.items():
        path = run_dir / "skill-outputs" / relative_path
        value = path.read_text(encoding="utf-8-sig").strip() if path.is_file() else ""
        if not value:
            raise ValueError(f"Analysis run is incomplete. Missing or empty output: {path}")
        results[name] = value
    return results


def latest_run(channel: str) -> Path:
    """Return the newest completed run directory for a channel slug."""
    candidates = sorted(
        (RUNS_ROOT / channel).glob("V* - *"),
        key=lambda path: path.name.partition(" - ")[2],
        reverse=True,
    )
    for path in candidates:
        if not (path / "normalized" / "collection.json").is_file():
            continue
        try:
            read_completed_outputs(path)
        except (FileNotFoundError, ValueError):
            continue
        return path
    raise FileNotFoundError(f"No completed run found for channel: {channel}. Finish the analysis before exporting.")


def read_analysis(run_dir: Path, channel_url: str) -> dict[str, str]:
    outputs = read_completed_outputs(run_dir)
    collection = json.loads(
        (run_dir / "normalized" / "collection.json").read_text(encoding="utf-8")
    )
    if outputs["Issues"].casefold() == NO_CHANNEL_ISSUES:
        outputs["Issues"] = ""
    country = collection.get("channel", {}).get("snippet", {}).get("country", "")
    return {
        "Business Name": collection.get("channel", {}).get("snippet", {}).get("title", ""),
        "YouTube Channel Link": sheet_channel_link(channel_url),
        "Subscribers": str(collection.get("channel", {}).get("statistics", {}).get("subscriberCount", "")),
        "Country": COUNTRIES.get(country, country),
        **outputs,
    }


def update_matching_rows(
    channel_url: str,
    sheet_name: str,
    run_dir: Path,
    spreadsheet_id: str | None = None,
    columns_path: Path = DEFAULT_COLUMNS_PATH,
    sheet_url_path: Path = DEFAULT_SHEET_URL_PATH,
) -> int:
    data = read_analysis(run_dir, channel_url)
    spreadsheet_id = spreadsheet_id or spreadsheet_id_from_url(sheet_url_path)
    credentials = authorize()
    service = build("sheets", "v4", credentials=credentials, cache_discovery=False)
    values = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id, range=sheet_range(sheet_name, "A:ZZ")
    ).execute().get("values", [])
    if not values:
        raise ValueError("The Google Sheet is empty.")
    headers = values[0]
    # The row lookup already includes the headers. Reuse them for the cache
    # refresh and target the current positions even during the cooldown.
    load_or_refresh_columns(spreadsheet_id, sheet_name, columns_path=columns_path, headers=headers)
    columns = {str(item["name"]): item for item in map_headers(headers)}
    required = ["Business Name", "YouTube Channel Link", "Channel Category", "Subscribers", "Niche", "Country", "Issues"]
    missing = [name for name in required if name not in columns]
    if missing:
        raise ValueError(f"Missing required Google Sheet columns: {', '.join(missing)}")
    url_index = int(columns["YouTube Channel Link"]["index"])
    wanted = sheet_channel_link(channel_url).casefold()
    rows = [
        index for index, row in enumerate(values[1:], start=2)
        if len(row) > url_index and sheet_channel_link(str(row[url_index])).casefold() == wanted
    ]
    if not rows:
        return 0

    updates = []
    for row_number in rows:
        for name, value in data.items():
            cell = f"{columns[name]['letter']}{row_number}"
            updates.append({"range": sheet_range(sheet_name, cell), "values": [[value]]})
    service.spreadsheets().values().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={"valueInputOption": "USER_ENTERED", "data": updates},
    ).execute()
    return len(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Update matching Google Sheet rows from a completed channel run.")
    run_source = parser.add_mutually_exclusive_group(required=True)
    run_source.add_argument("--channel", help="Find the latest completed run for this channel folder.")
    run_source.add_argument("--run-dir", type=Path, help="Use this exact completed run directory.")
    parser.add_argument("--channel-url", required=True)
    parser.add_argument("--sheet-name")
    parser.add_argument("--spreadsheet-id")
    args = parser.parse_args()
    spreadsheet_id = args.spreadsheet_id or spreadsheet_id_from_url()
    sheet_name = args.sheet_name or cached_sheet_name(spreadsheet_id)
    if not sheet_name:
        parser.error("Provide --sheet-name when the spreadsheet has no cached tab.")
    run_dir = args.run_dir if args.run_dir is not None else latest_run(args.channel)
    try:
        count = update_matching_rows(args.channel_url, sheet_name, run_dir, spreadsheet_id)
    except Exception as exc:
        if run_dir.is_dir():
            write_export_status(run_dir, "failed")
        parser.exit(1, f"{exc}\n")
    write_export_status(run_dir, "updated" if count else "no_matching_rows", count)
    print(f"Updated {count} matching row(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
