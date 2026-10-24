"""Generate normalized inputs for downstream skills based on quick-analysis-inputs.json."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.collectors.youtube_data_api import write_json

DEFAULT_CONFIG_PATH = Path("config/quick-analysis-inputs.json")


def load_inputs_config(config_path: Path = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    if not config_path.exists():
        return {}
    return json.loads(config_path.read_text(encoding="utf-8"))


def build_channel_categorization_data(
    channel_data: dict[str, Any],
    recent_videos: list[dict[str, Any]],
    config: dict[str, Any],
) -> dict[str, Any]:
    snippet = channel_data.get("snippet", {})
    output: dict[str, Any] = {}

    if config.get("channel_name"):
        output["channel_name"] = snippet.get("title", "")
    if config.get("channel_description"):
        output["channel_description"] = snippet.get("description", "")

    total_limit = config.get("total_videos", len(recent_videos))
    selected_videos = recent_videos[:total_limit]

    videos_config = config.get("videos", [{}])
    video_rule = videos_config[0] if isinstance(videos_config, list) and videos_config else {}

    include_title = video_rule.get("title", True)
    include_desc = video_rule.get("description", True)

    formatted_videos: list[dict[str, Any]] = []
    for vid in selected_videos:
        v_snippet = vid.get("snippet", {})
        item: dict[str, Any] = {}
        if include_title:
            item["title"] = v_snippet.get("title", "")
        if include_desc:
            item["description"] = v_snippet.get("description", "")
        formatted_videos.append(item)

    output["total_videos"] = len(formatted_videos)
    output["videos"] = formatted_videos
    return output


def prepare_skill_inputs(
    run_dir: Path,
    channel_data: dict[str, Any],
    recent_videos: list[dict[str, Any]],
    config_path: Path = DEFAULT_CONFIG_PATH,
) -> dict[str, Path]:
    """Generates the required skill input files in run_dir/normalized."""
    config = load_inputs_config(config_path)
    normalized_dir = run_dir / "normalized"
    normalized_dir.mkdir(parents=True, exist_ok=True)
    created_files: dict[str, Path] = {}

    # 1. Channel Categorization
    categorization_cfg = config.get("channel_categorization")
    if categorization_cfg:
        cat_data = build_channel_categorization_data(channel_data, recent_videos, categorization_cfg)
        cat_file = normalized_dir / "data-for-channel-categorization.json"
        write_json(cat_file, cat_data)
        created_files["categorization"] = cat_file

    # 2. Channel Niche Search (Placeholder ready for when configured)
    niche_cfg = config.get("channel_niche_search")
    if niche_cfg:
        niche_file = normalized_dir / "data-for-channel-niche-search.json"
        write_json(niche_file, niche_cfg)
        created_files["niche_search"] = niche_file

    # 3. Channel Issues (Placeholder ready for when configured)
    issues_cfg = config.get("channel_issues")
    if issues_cfg:
        issues_file = normalized_dir / "data-for-channel-issues.json"
        write_json(issues_file, issues_cfg)
        created_files["issues"] = issues_file

    return created_files
