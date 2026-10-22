"""Run the metadata collector and emit a quick channel analysis."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from src.analysis.quick_channel import analyze_quick_channel, render_quick_analysis
from src.collectors.youtube_data_api import YouTubeAPIError, YouTubeClient, collect_channel, load_dotenv, write_json


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
    """Collect shared metadata once, then generate a quick-only analysis."""
    return analyze_collected_run(collect_channel(channel_input, output_root, client))


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
