"""Generate normalized inputs for downstream skills based on quick-analysis-inputs.json."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.collectors.youtube_data_api import write_json

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config/quick-analysis-inputs.json"


def load_inputs_config(config_path: Path = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(config, dict) or set(config) - {"channel_categorization", "channel_niche_search", "channel_issues"}:
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


def build_skill_data(channel_data, recent_videos, config, collected=None):
    collected = collected or {}
    if not isinstance(config, dict):
        raise ValueError("Skill configuration must be an object.")
    sections = {"videos", "shorts", "playlists", "community_posts"}
    allowed = set(CHANNEL_PATHS) | sections | {"total_videos", "total_shorts", "total_playlists", "total_community_posts", "collection_metadata"}
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

    sections = {"channel_categorization": ("categorization", "data-for-channel-categorization.json"),
                "channel_niche_search": ("niche_search", "data-for-channel-niche-search.json"),
                "channel_issues": ("issues", "data-for-channel-issues.json")}
    prepared = []
    for section, (key, filename) in sections.items():
        rule = config.get(section, {})
        if not isinstance(rule, dict):
            raise ValueError(f"{section} must be an object.")
        if rule:
            prepared.append((key, normalized_dir / filename, build_skill_data(channel_data, recent_videos, rule, collected)))
    for key, path, data in prepared:
        write_json(path, data)
        created_files[key] = path

    return created_files
