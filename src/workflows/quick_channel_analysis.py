"""Run the metadata collector and emit a quick channel analysis."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from src.analysis.quick_channel import analyze_quick_channel, render_quick_analysis
from src.analysis.skill_inputs import prepare_skill_inputs
from src.collectors.youtube_data_api import YouTubeAPIError, YouTubeClient, collect_channel, load_dotenv, write_json
from src.collectors.youtube_recent_videos import _recent_video_ids, PLAYLIST_FIELDS, PLAYLIST_PARTS


def analyze_collected_run(run_dir: Path) -> Path:
    collection_path = run_dir / "normalized" / "collection.json"
    collection = json.loads(collection_path.read_text(encoding="utf-8"))
    analysis = analyze_quick_channel(collection)
    json_path = run_dir / "analysis" / "quick-channel-analysis.json"
    text_path = run_dir / "quick-channel-analysis.txt"
    write_json(json_path, analysis)
    text_path.write_text(render_quick_analysis(analysis), encoding="utf-8")
    return text_path


def run(channel_input: str, output_root: Path, client: YouTubeClient) -> Path:
    """Collect channel data and recent videos, generate skill inputs, then run quick analysis."""
    run_dir = collect_channel(channel_input, output_root, client)
    collection_path = run_dir / "normalized" / "collection.json"
    collection = json.loads(collection_path.read_text(encoding="utf-8"))
    channel = collection.get("channel", {})

    # Fetch up to 50 recent videos to supply downstream skills
    channel_id = channel.get("id", "")
    uploads_id = "UU" + channel_id[2:] if channel_id.startswith("UC") else None
    recent_videos: list[dict[str, Any]] = []

    if uploads_id:
        try:
            video_ids = _recent_video_ids(uploads_id, client, limit=50, raw_dir=run_dir / "raw")
            if video_ids:
                videos_res = client.get(
                    "videos",
                    part="snippet,contentDetails",
                    fields="items(id,snippet(publishedAt,title,description),contentDetails(duration))",
                    id=",".join(video_ids),
                    maxResults=50,
                )
                write_json(run_dir / "raw" / "recent-videos-response.json", videos_res)
                v_map = {v.get("id"): v for v in videos_res.get("items", [])}
                recent_videos = [v_map[vid] for vid in video_ids if vid in v_map]
        except Exception:
            pass

    prepare_skill_inputs(run_dir=run_dir, channel_data=channel, recent_videos=recent_videos)
    return analyze_collected_run(run_dir)


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect metadata and create a quick YouTube channel analysis.")
    parser.add_argument("channel", help="Channel URL, @handle, legacy username URL, or UC channel ID")
    parser.add_argument("--output", default="runs")
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()
    load_dotenv()
    api_key = os.environ.get("YOUTUBE_API_KEY", "")
    if not api_key or api_key == "replace-me":
        print("ERROR: Set YOUTUBE_API_KEY in .env or the environment.", file=sys.stderr)
        return 2
    try:
        analysis_path = run(args.channel, Path(args.output), YouTubeClient(api_key, args.timeout))
    except (ValueError, YouTubeAPIError, OSError, KeyError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(analysis_path.read_text(encoding="utf-8"), end="")
    print(f"Report: {analysis_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
