"""Run the metadata collector and emit a quick channel analysis."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from src.collectors.configured_collection import DEFAULT_PROFILE, collect_configured

from src.analysis.quick_channel import analyze_quick_channel, render_quick_analysis
from src.analysis.skill_inputs import DEFAULT_CONFIG_PATH, load_inputs_config, prepare_skill_inputs, prepare_skill_outputs
from src.collectors.youtube_data_api import YouTubeAPIError, YouTubeClient, load_dotenv, normalize_channel_input, write_json


def analyze_collected_run(run_dir: Path) -> Path:
    collection_path = run_dir / "normalized" / "collection.json"
    collection = json.loads(collection_path.read_text(encoding="utf-8"))
    output_dir = run_dir / "skill-outputs"
    category_path = output_dir / "channel-categorization-output.md"
    niche_path = output_dir / "channel-niche-search-output.md"
    channel_issues_path = output_dir / "channel-issues" / "channel-issues-orchestrator-output.md"
    analysis = analyze_quick_channel(collection)
    pending = []
    if category_path.exists() and category_path.read_text(encoding="utf-8").strip():
        analysis["channel_category"] = category_path.read_text(encoding="utf-8").strip()
    else:
        pending.append("youtube-channel-categorization")
    if niche_path.exists() and niche_path.read_text(encoding="utf-8").strip():
        analysis["channel_niches"] = [niche_path.read_text(encoding="utf-8").strip()]
    else:
        pending.append("find-channel-niches")
    if channel_issues_path.exists() and channel_issues_path.read_text(encoding="utf-8").strip():
        analysis["channel_issues"] = [line.strip() for line in channel_issues_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    else:
        pending.append("channel-issues-orchestrator")
    if pending:
        analysis["pending_skill_outputs"] = pending
    json_path = run_dir / "analysis" / "quick-channel-analysis.json"
    text_path = run_dir / "quick-channel-analysis.txt"
    write_json(json_path, analysis)
    text_path.write_text(render_quick_analysis(analysis), encoding="utf-8")
    return text_path


def run(channel_input: str, output_root: Path, client: YouTubeClient, profile_path: Path = DEFAULT_PROFILE,
        inputs_path: Path = DEFAULT_CONFIG_PATH) -> Path:
    """Collect channel data and recent videos, generate skill inputs, then run quick analysis."""
    inputs_config = load_inputs_config(inputs_path)
    thumbnail_limit = inputs_config.get("channel_issues", {}).get("thumbnail-analysis-skill", {}).get("total_videos")
    normalized_input = normalize_channel_input(channel_input)
    run_dir, collected = collect_configured(normalized_input, output_root, client, profile_path, thumbnail_limit)
    collection_path = run_dir / "normalized" / "collection.json"
    collection = json.loads(collection_path.read_text(encoding="utf-8"))
    channel = collection.get("channel", {})

    prepare_skill_inputs(run_dir=run_dir, channel_data=channel, recent_videos=collected["videos"],
                         config_path=inputs_path, collected=collected)
    prepare_skill_outputs(run_dir=run_dir, config_path=inputs_path)
    return analyze_collected_run(run_dir)


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect metadata and create a quick YouTube channel analysis.")
    parser.add_argument("channel", help="Channel URL, @handle, legacy username URL, or UC channel ID")
    parser.add_argument("--output", default="runs")
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--collection-config", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument("--inputs-config", type=Path, default=DEFAULT_CONFIG_PATH)
    args = parser.parse_args()
    load_dotenv()
    api_key = os.environ.get("YOUTUBE_API_KEY", "")
    if not api_key or api_key == "replace-me":
        print("ERROR: Set YOUTUBE_API_KEY in .env or the environment.", file=sys.stderr)
        return 2
    try:
        analysis_path = run(args.channel, Path(args.output), YouTubeClient(api_key, args.timeout),
                            args.collection_config, args.inputs_config)
    except (ValueError, YouTubeAPIError, OSError, KeyError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(analysis_path.read_text(encoding="utf-8"), end="")
    print(f"Report: {analysis_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
