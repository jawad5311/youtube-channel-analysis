"""Collect public channel metadata with YouTube Data API v3.

Run: python -m src.collectors.youtube_data_api https://youtube.com/@GoogleDevelopers
Set YOUTUBE_API_KEY in the environment or a local .env file.
"""
from __future__ import annotations
import argparse, json, os, re, sys, time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen
from src.validators.quality import build_quality_report

API = "https://www.googleapis.com/youtube/v3"
CHANNEL_PARTS = "snippet,statistics,status,topicDetails,brandingSettings"
CHANNEL_FIELDS = (
    "items(id,"
    "snippet(title,description,country),"
    "statistics(viewCount,subscriberCount,videoCount),"
    "topicDetails(topicIds,topicCategories),"
    "status(madeForKids),"
    "brandingSettings/channel(title,description,keywords,defaultLanguage,country))"
)

class YouTubeAPIError(RuntimeError): pass

@dataclass(frozen=True)
class ChannelReference:
    filter_name: str
    filter_value: str

def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def load_dotenv(path: Path = Path(".env")) -> None:
    if not path.exists(): return
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("'\""))

def parse_channel_reference(value: str) -> ChannelReference:
    value = value.strip()
    if re.fullmatch(r"UC[A-Za-z0-9_-]{22}", value): return ChannelReference("id", value)
    if value.startswith("@") and len(value) > 1: return ChannelReference("forHandle", value)
    parsed = urlparse(value if "://" in value else f"https://{value}")
    if (parsed.hostname or "").lower() not in {"youtube.com", "www.youtube.com", "m.youtube.com"}:
        raise ValueError("Expected a youtube.com channel URL, @handle, or channel ID.")
    parts = [p for p in parsed.path.split("/") if p]
    if not parts: raise ValueError("The URL does not identify a channel.")
    if parts[0].startswith("@"): return ChannelReference("forHandle", parts[0])
    if len(parts) >= 2 and parts[0] == "channel": return ChannelReference("id", parts[1])
    if len(parts) >= 2 and parts[0] == "user": return ChannelReference("forUsername", parts[1])
    raise ValueError("Use /@handle, /channel/UC..., /user/name, a handle, or a channel ID.")

class YouTubeClient:
    def __init__(self, api_key: str, timeout: int = 30, retries: int = 3):
        if not api_key: raise ValueError("YOUTUBE_API_KEY is missing.")
        self.api_key, self.timeout, self.retries, self.request_count = api_key, timeout, retries, 0

    def get(self, resource: str, **params: Any) -> dict[str, Any]:
        params = {k: v for k, v in params.items() if v is not None}; params["key"] = self.api_key
        url = f"{API}/{resource}?{urlencode(params)}"
        for attempt in range(self.retries + 1):
            try:
                with urlopen(Request(url, headers={"Accept": "application/json"}), timeout=self.timeout) as response:
                    self.request_count += 1
                    return json.loads(response.read().decode("utf-8"))
            except HTTPError as exc:
                self.request_count += 1; body = exc.read().decode("utf-8", errors="replace")
                if exc.code in {429, 500, 502, 503, 504} and attempt < self.retries:
                    time.sleep(2 ** attempt); continue
                try: message = json.loads(body)["error"]["message"]
                except (KeyError, TypeError, json.JSONDecodeError): message = body or str(exc)
                raise YouTubeAPIError(f"YouTube API HTTP {exc.code}: {message}") from exc
            except URLError as exc:
                if attempt < self.retries: time.sleep(2 ** attempt); continue
                raise YouTubeAPIError(f"YouTube API connection failed: {exc.reason}") from exc
        raise AssertionError("Retry loop ended unexpectedly")

def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)

def slug(value: str) -> str:
    return (re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "youtube-channel")[:80]

def collect_channel(channel_input: str, output_root: Path, client: YouTubeClient) -> Path:
    ref = parse_channel_reference(channel_input)
    channel_response = client.get(
        "channels",
        part=CHANNEL_PARTS,
        fields=CHANNEL_FIELDS,
        **{ref.filter_name: ref.filter_value},
    )
    if not channel_response.get("items"): raise YouTubeAPIError(f"No channel found for {channel_input!r}.")
    channel = channel_response["items"][0]; channel_id = channel["id"]
    name = channel.get("snippet", {}).get("title", channel_id)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir, raw_dir = output_root / slug(name) / run_id, output_root / slug(name) / run_id / "raw"
    raw_dir.mkdir(parents=True, exist_ok=False); (run_dir / "normalized").mkdir()
    write_json(raw_dir / "channel-response.json", channel_response)
    collection = {"schema_version": "0.1.0", "requested_input": channel_input, "collected_at": utc_now(),
                  "collection_scope": "channel_metadata", "channel": channel}
    quality = build_quality_report(channel=channel)
    write_json(run_dir / "normalized" / "collection.json", collection); write_json(run_dir / "quality-report.json", quality)
    manifest = {"schema_version": "0.1.0", "run_id": run_id, "status": "ready" if quality["quality_passed"] else "partial",
                "requested_input": channel_input, "channel_id": channel_id, "channel_name": name, "collected_at": collection["collected_at"],
                "collection_scope": "channel_metadata", "quality_passed": quality["quality_passed"], "api_requests": client.request_count}
    write_json(run_dir / "manifest.json", manifest)
    return run_dir

def main() -> int:
    parser = argparse.ArgumentParser(description="Collect public metadata for one YouTube channel.")
    parser.add_argument("channel", help="Channel URL, @handle, legacy username URL, or UC channel ID")
    parser.add_argument("--output", default="runs"); parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args(); load_dotenv(); key = os.environ.get("YOUTUBE_API_KEY", "")
    if not key or key == "replace-me": print("ERROR: Set YOUTUBE_API_KEY in .env or the environment.", file=sys.stderr); return 2
    try: run_dir = collect_channel(args.channel, Path(args.output), YouTubeClient(key, args.timeout))
    except (ValueError, YouTubeAPIError, OSError) as exc: print(f"ERROR: {exc}", file=sys.stderr); return 1
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    print(f"Collection status: {manifest['status']}\nChannel: {manifest['channel_name']} ({manifest['channel_id']})\nScope: {manifest['collection_scope']}\nRun directory: {run_dir}")
    return 0 if manifest["quality_passed"] else 3

if __name__ == "__main__": raise SystemExit(main())
