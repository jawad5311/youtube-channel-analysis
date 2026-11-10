"""Generate normalized inputs for downstream skills based on quick-analysis-inputs.json."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from src.collectors.youtube_data_api import write_json

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config/quick-analysis-inputs.json"
SKILL_SECTIONS = {
    "channel_categorization": "categorization",
    "channel_niche_search": "niche_search",
    "channel_issues": "issues",
    "video_seo_analysis": "video_seo",
}


def prepare_skill_outputs(run_dir: Path, config_path: Path = DEFAULT_CONFIG_PATH) -> dict[str, Path]:
    """Create one output placeholder for every configured skill."""
    config = load_inputs_config(config_path)
    output_dir = run_dir / "skill-outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    channel_issues_output_dir = output_dir / "channel-issues"
    channel_issues_output_dir.mkdir(parents=True, exist_ok=True)
    created: dict[str, Path] = {}

    def create(skill_name: str, filename: str) -> None:
        path = output_dir / filename
        path.write_text("", encoding="utf-8")
        created[skill_name] = path

    if config.get("channel_categorization"):
        create("channel-categorization", "channel-categorization-output.md")
    if config.get("channel_niche_search"):
        create("channel-niche-search", "channel-niche-search-output.md")
    for skill_name in config.get("channel_issues", {}):
        if skill_name == "skill_input_file":
            continue
        filename = skill_name + "-output.md"
        path = channel_issues_output_dir / filename
        path.write_text("", encoding="utf-8")
        created[skill_name] = path
    return created


def load_inputs_config(config_path: Path = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(config, dict) or set(config) - set(SKILL_SECTIONS):
        raise ValueError("Unsupported skill-input section.")
    return config


CHANNEL_PATHS = {
    "channel_name": ("snippet", "title"), "channel_description": ("snippet", "description"),
    "channel_tags": ("brandingSettings", "channel", "keywords"),
    "channel_keywords": ("brandingSettings", "channel", "keywords"),
    "country": ("snippet", "country"), "subscriber_count": ("statistics", "subscriberCount"),
    "branding_title": ("brandingSettings", "channel", "title"),
    "branding_description": ("brandingSettings", "channel", "description"),
    "topic_categories": ("topicDetails", "topicCategories"),
    "banner_image": ("brandingSettings", "image", "bannerExternalUrl"),
}
RECORD_PATHS = {key: ("snippet", key) for key in
                ("title", "description", "tags", "publishedAt", "thumbnails", "liveBroadcastContent")}
RECORD_PATHS.update(duration=("contentDetails", "duration"), viewCount=("statistics", "viewCount"))


def _read(record, path):
    for key in path:
        if not isinstance(record, dict) or key not in record:
            return None
        record = record[key]
    return record


def _select_records(records, rule, paths, label, limit):
    if type(limit) is not int or limit < 0:
        raise ValueError(f"Invalid {label} limit.")
    if isinstance(rule, list):
        if len(rule) != 1 or not isinstance(rule[0], dict):
            raise ValueError(f"{label} needs one field-selection object.")
        rule = rule[0]
    if not isinstance(rule, dict) or set(rule) - set(paths):
        raise ValueError(f"Unsupported {label} fields.")
    if any(type(v) is not bool for v in rule.values()):
        raise ValueError(f"{label} fields must be boolean.")
    output, missing = [], []
    for index, record in enumerate(records[:limit]):
        selected = {}
        for field, enabled in rule.items():
            if enabled:
                value = _read(record, paths[field])
                if value is None:
                    missing.append(f"{label}[{index}].{field}")
                else:
                    selected[field] = value
        output.append(selected)
    return output, missing


def _remove_view_outliers(records: list[dict[str, Any]], high_count: int, low_count: int):
    ranked = [(index, item) for index, item in enumerate(records)
              if isinstance(item.get("viewCount"), (int, float)) or str(item.get("viewCount", "")).isdigit()]
    ranked.sort(key=lambda pair: int(pair[1]["viewCount"]))
    low_indexes = {index for index, _ in ranked[:low_count]}
    high_indexes = {index for index, _ in ranked[-high_count:]} if high_count else set()
    excluded = []
    kept = []
    for index, item in enumerate(records):
        if index in low_indexes or index in high_indexes:
            excluded.append(item)
        else:
            kept.append(item)
    return kept, excluded


def build_performance_skill_data(channel_data, recent_videos, config, collected=None):
    """Prepare chronological video reach data for the performance skill."""
    collected = collected or {}
    subscriber_value = _read(channel_data, CHANNEL_PATHS["subscriber_count"])
    try:
        subscriber_count = int(subscriber_value)
    except (TypeError, ValueError):
        subscriber_count = 0
    limit = config.get("total_videos", len(recent_videos))
    rule = config.get("videos", [{"title": True, "publishedAt": True, "viewCount": True}])
    max_age_months = config.get("max_age_months", 0)
    if type(max_age_months) is not int or not 0 <= max_age_months <= 12:
        raise ValueError("max_age_months must be an integer from 0 through 12.")
    source_videos = recent_videos
    if max_age_months:
        cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_months * 30.4375)
        source_videos = []
        for video in recent_videos:
            published = video.get("snippet", {}).get("publishedAt")
            try:
                published_at = datetime.fromisoformat(published.replace("Z", "+00:00"))
            except (AttributeError, ValueError):
                continue
            if published_at >= cutoff:
                source_videos.append(video)
    selected, missing = _select_records(source_videos, rule, RECORD_PATHS, "videos", limit)
    selected.sort(key=lambda item: item.get("publishedAt") or "", reverse=True)
    high_count = config.get("high_view_outliers", 0)
    low_count = config.get("low_view_outliers", 0)
    available_count = len(selected)
    high_removed = min(high_count, available_count)
    low_removed = min(low_count, max(0, available_count - high_removed))
    selected, excluded = _remove_view_outliers(selected, high_count, low_count)
    videos = []
    for item in selected:
        try:
            views = int(item.get("viewCount", 0))
        except (TypeError, ValueError):
            views = 0
        reach = round((views / subscriber_count) * 100, 2) if subscriber_count else None
        videos.append({
            "title": item.get("title"),
            "publishedAt": item.get("publishedAt"),
            "viewCount": views,
            "reachPercent": reach,
        })
    valid_views = [video["viewCount"] for video in videos]
    valid_reach = [video["reachPercent"] for video in videos if video["reachPercent"] is not None]
    output = {
        "subscriber_count": subscriber_count,
        "total_videos_analyzed": len(videos),
        "total_views": sum(valid_views),
        "average_views": round(sum(valid_views) / len(valid_views), 2) if valid_views else 0,
        "average_view_percentage": round(sum(valid_reach) / len(valid_reach), 2) if valid_reach else None,
        "high_view_outliers_removed": high_removed,
        "low_view_outliers_removed": low_removed,
        "videos": videos,
    }
    if missing:
        output["missing_data"] = missing
    return output


def build_skill_data(channel_data, recent_videos, config, collected=None):
    collected = collected or {}
    if not isinstance(config, dict):
        raise ValueError("Skill configuration must be an object.")
    sections = {"videos", "shorts", "playlists", "community_posts"}
    allowed = set(CHANNEL_PATHS) | sections | {"skill_input_file", "max_age_months", "high_view_outliers", "low_view_outliers", "total_videos", "total_shorts", "total_playlists", "total_community_posts", "collection_metadata"}
    if set(config) - allowed:
        raise ValueError(f"Unsupported skill-input fields: {sorted(set(config) - allowed)}")
    output, missing = {}, []
    for key, path in CHANNEL_PATHS.items():
        if key in config and type(config[key]) is not bool:
            raise ValueError(f"{key} must be boolean.")
        if config.get(key):
            value = _read(channel_data, path)
            if value is None:
                missing.append(key)
            else:
                output[key] = value
    community = collected.get("community_posts", {})
    sources = {
        "videos": (recent_videos, RECORD_PATHS),
        "shorts": (collected.get("shorts_candidates", []), RECORD_PATHS),
        "playlists": (collected.get("playlists", []), {f: (f,) for f in ("title", "description", "itemCount")}),
        "community_posts": (community.get("posts", []), {f: (f,) for f in ("text", "publishedAt", "pinned")}),
    }
    for section, (records, paths) in sources.items():
        if section not in config or config[section] is False:
            continue
        count_key = "total_" + section
        selected, absent = _select_records(records, config[section], paths, section, config.get(count_key, len(records)))
        output[section] = selected
        output[count_key] = len(selected)
        if section == "videos" and (config.get("high_view_outliers") or config.get("low_view_outliers")):
            high_count = config.get("high_view_outliers", 0)
            low_count = config.get("low_view_outliers", 0)
            if type(high_count) is not int or high_count < 0 or type(low_count) is not int or low_count < 0:
                raise ValueError("Video outlier counts must be nonnegative integers.")
            output[section], excluded = _remove_view_outliers(selected, high_count, low_count)
            output[count_key] = len(output[section])
            output["excluded_view_outliers"] = excluded
        missing.extend(absent)
        if config.get(count_key, 0) > len(records):
            missing.append(f"{section}: requested {config[count_key]}, available {len(records)}")
        if section == "shorts":
            output["shorts_status"] = "unconfirmed_candidates"
        if section == "community_posts":
            output["community_status"] = community.get("status", "not_collected")
        if section == "playlists":
            output["playlist_status"] = collected.get("playlist_status", "not_collected")
    if config.get("collection_metadata"):
        output["collection_metadata"] = collected.get("collection_metadata", {})
    if missing:
        output["missing_data"] = missing
    return output


def build_channel_categorization_data(
    channel_data: dict[str, Any],
    recent_videos: list[dict[str, Any]],
    config: dict[str, Any],
) -> dict[str, Any]:
    return build_skill_data(channel_data, recent_videos, config)


def prepare_skill_inputs(
    run_dir: Path,
    channel_data: dict[str, Any],
    recent_videos: list[dict[str, Any]],
    config_path: Path = DEFAULT_CONFIG_PATH,
    collected: dict[str, Any] | None = None,
) -> dict[str, Path]:
    """Generates the required skill input files in run_dir/normalized."""
    config = load_inputs_config(config_path)
    normalized_dir = run_dir / "normalized"
    normalized_dir.mkdir(parents=True, exist_ok=True)
    created_files: dict[str, Path] = {}

    prepared = []
    for section, key in SKILL_SECTIONS.items():
        rule = config.get(section, {})
        if not isinstance(rule, dict):
            raise ValueError(f"{section} must be an object.")
        skill_input_file = rule.get("skill_input_file")
        if skill_input_file is not None:
            if not isinstance(skill_input_file, str) or not skill_input_file.strip():
                raise ValueError(f"{section}.skill_input_file must be a relative path in normalized/.")
            output_path = (normalized_dir / skill_input_file).resolve()
            if output_path.parent != normalized_dir.resolve() and not str(output_path).startswith(str(normalized_dir.resolve()) + "\\"):
                raise ValueError(f"{section}.skill_input_file must stay inside normalized/.")
        if section == "channel_issues" and rule and all(isinstance(value, dict) for name, value in rule.items() if name != "skill_input_file"):
            for skill, selection in rule.items():
                if skill == "skill_input_file" or not selection:
                    continue
                child_file = selection.get("skill_input_file")
                if not child_file:
                    raise ValueError(f"{skill}.skill_input_file is required.")
                child_path = (normalized_dir / child_file).resolve()
                if not str(child_path).startswith(str(normalized_dir.resolve()) + "\\"):
                    raise ValueError(f"{skill}.skill_input_file must stay inside normalized/.")
                clean_selection = {k: v for k, v in selection.items() if k != "skill_input_file"}
                data = (build_performance_skill_data(channel_data, recent_videos, clean_selection, collected)
                        if skill == "performance-analysis-skill" else
                        build_skill_data(channel_data, recent_videos, clean_selection, collected))
                prepared.append((skill, child_path, data))
        elif rule:
            selection = {k: v for k, v in rule.items() if k != "skill_input_file"}
            if not skill_input_file:
                raise ValueError(f"{section}.skill_input_file is required.")
            prepared.append((key, normalized_dir / skill_input_file, build_skill_data(channel_data, recent_videos, selection, collected)))
    for key, path, data in prepared:
        write_json(path, data)
        created_files[key] = path

    return created_files

