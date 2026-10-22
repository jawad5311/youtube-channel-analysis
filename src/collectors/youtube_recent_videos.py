"""Collect a recent sample of public YouTube videos for later analysis."""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.collectors.youtube_data_api import (
    YouTubeAPIError,
    YouTubeClient,
    load_dotenv,
    parse_channel_reference,
    slug,
    utc_now,
    write_json,
)

CHANNEL_PARTS = "snippet,contentDetails"
CHANNEL_FIELDS = "items(id,snippet(title),contentDetails(relatedPlaylists(uploads)))"
PLAYLIST_PARTS = "snippet,contentDetails"
PLAYLIST_FIELDS = (
    "items(snippet(publishedAt,title,description,thumbnails,resourceId(videoId)),"
    "contentDetails(videoId,videoPublishedAt)),nextPageToken"
)
VIDEO_PARTS = "snippet,contentDetails,statistics,status"
VIDEO_FIELDS = (
    "items(id,snippet(publishedAt,title,description,thumbnails,tags,categoryId,liveBroadcastContent),"
    "contentDetails(duration,caption),statistics(viewCount,likeCount,commentCount),status(privacyStatus))"
)


def _channel_for_input(channel_input: str, client: YouTubeClient) -> tuple[dict[str, Any], str]:
    ref = parse_channel_reference(channel_input)
    response = client.get(
        "channels",
        part=CHANNEL_PARTS,
        fields=CHANNEL_FIELDS,
        **{ref.filter_name: ref.filter_value},
    )
    if not response.get("items"):
        raise YouTubeAPIError(f"No channel found for {channel_input!r}.")
    channel = response["items"][0]
    uploads = channel.get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads")
    if not uploads:
        raise YouTubeAPIError("Channel has no uploads playlist in the response.")
    return channel, uploads


def _recent_video_ids(
    uploads_playlist_id: str,
    client: YouTubeClient,
    limit: int,
    raw_dir: Path,
) -> list[str]:
    response = client.get(
        "playlistItems",
        part=PLAYLIST_PARTS,
        fields=PLAYLIST_FIELDS,
        playlistId=uploads_playlist_id,
        maxResults=min(limit, 50),
    )
    write_json(raw_dir / "uploads-playlist-page-0001.json", response)
    return [
        item.get("contentDetails", {}).get("videoId")
        or item.get("snippet", {}).get("resourceId", {}).get("videoId")
        for item in response.get("items", [])
    ][:limit]


def collect_recent_videos(
    channel_input: str,
    output_root: Path,
    client: YouTubeClient,
    limit: int = 10,
) -> Path:
    """Collect the newest public uploads and return their run directory."""
    if limit < 1 or limit > 50:
        raise ValueError("Recent video limit must be between 1 and 50.")

    channel, uploads_playlist_id = _channel_for_input(channel_input, client)
    channel_name = channel.get("snippet", {}).get("title", channel["id"])
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = output_root / slug(channel_name) / run_id
    raw_dir = run_dir / "raw"
    (run_dir / "normalized").mkdir(parents=True, exist_ok=False)
    raw_dir.mkdir(parents=True, exist_ok=False)

    write_json(raw_dir / "channel-response.json", {"items": [channel]})
    video_ids = _recent_video_ids(uploads_playlist_id, client, limit, raw_dir)
    videos_response = client.get(
        "videos",
        part=VIDEO_PARTS,
        fields=VIDEO_FIELDS,
        id=",".join(video_ids),
        maxResults=50,
    )
    write_json(raw_dir / "videos-response.json", videos_response)

    videos_by_id = {video.get("id"): video for video in videos_response.get("items", [])}
    videos = [videos_by_id[video_id] for video_id in video_ids if video_id in videos_by_id]
    collection = {
        "schema_version": "0.1.0",
        "requested_input": channel_input,
        "collected_at": utc_now(),
        "collection_scope": "recent_videos",
        "channel_id": channel["id"],
        "channel_name": channel_name,
        "uploads_playlist_id": uploads_playlist_id,
        "requested_limit": limit,
        "videos": videos,
    }
    write_json(run_dir / "normalized" / "recent-videos.json", collection)
    manifest = {
        "schema_version": "0.1.0",
        "run_id": run_id,
        "status": "ready" if videos else "partial",
        "requested_input": channel_input,
        "channel_id": channel["id"],
        "channel_name": channel_name,
        "collected_at": collection["collected_at"],
        "collection_scope": "recent_videos",
        "requested_limit": limit,
        "videos_retrieved": len(videos),
        "quality_passed": bool(videos) and len(videos) == len(video_ids),
        "api_requests": client.request_count,
    }
    write_json(run_dir / "manifest.json", manifest)
    return run_dir


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect recent public videos for one YouTube channel.")
    parser.add_argument("channel", help="Channel URL, @handle, legacy username URL, or UC channel ID")
    parser.add_argument("--limit", type=int, default=10, help="Number of recent uploads to collect (default: 10)")
    parser.add_argument("--output", default="runs")
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()
    load_dotenv()
    api_key = os.environ.get("YOUTUBE_API_KEY", "")
    if not api_key or api_key == "replace-me":
        print("ERROR: Set YOUTUBE_API_KEY in .env or the environment.", file=sys.stderr)
        return 2
    try:
        run_dir = collect_recent_videos(args.channel, Path(args.output), YouTubeClient(api_key, args.timeout), args.limit)
    except (ValueError, YouTubeAPIError, OSError, KeyError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    print(
        f"Collection status: {manifest['status']}\n"
        f"Channel: {manifest['channel_name']} ({manifest['channel_id']})\n"
        f"Videos retrieved: {manifest['videos_retrieved']}\n"
        f"Scope: {manifest['collection_scope']}\n"
        f"Run directory: {run_dir}"
    )
    return 0 if manifest["quality_passed"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
