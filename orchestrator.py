"""Collect one YouTube channel and prepare the skill handoff for Codex."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from src.analysis.skill_inputs import DEFAULT_CONFIG_PATH, prepare_skill_inputs, prepare_skill_outputs
from src.collectors.configured_collection import DEFAULT_PROFILE, collect_configured
from src.collectors.youtube_data_api import YouTubeAPIError, YouTubeClient, load_dotenv, normalize_channel_input, write_json
from src.workflows.run_cleanup import clean_run_root

PROJECT_ROOT = Path(__file__).resolve().parent
SKILL_MANIFEST_PATH = PROJECT_ROOT / "config" / "skill-manifest.json"


def load_skill_manifest(path: Path = SKILL_MANIFEST_PATH) -> dict[str, Any]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or not isinstance(manifest.get("skills"), list):
        raise ValueError("Skill manifest must contain a skills list.")
    return manifest


def resolve_skill_manifest(manifest: dict[str, Any], project_root: Path, run_root: Path) -> dict[str, Any]:
    resolved = dict(manifest)
    parent = dict(manifest.get("parent_skill", {}))
    if parent.get("instructions"):
        parent["instructions"] = str((project_root / parent["instructions"]).resolve())
    resolved["parent_skill"] = parent
    skills = []
    for skill in sorted(manifest["skills"], key=lambda item: item.get("order", 0)):
        item = dict(skill)
        item["instructions"] = str((project_root / item["instructions"]).resolve())
        item["input"] = str((run_root / item["input"]).resolve())
        item["output"] = str((run_root / item["output"]).resolve())
        skills.append(item)
    resolved["skills"] = skills
    resolved["run_root"] = str(run_root.resolve())
    return resolved


def write_run_manifest(run_root: Path) -> Path:
    path = run_root / "manifest.json"
    write_json(path, resolve_skill_manifest(load_skill_manifest(), PROJECT_ROOT, run_root))
    return path


def prepare_run(channel_input: str, output_root: Path, client: YouTubeClient,
                profile_path: Path = DEFAULT_PROFILE,
                inputs_path: Path = DEFAULT_CONFIG_PATH) -> tuple[Path, Path]:
    """Collect data and create all normalized inputs and output placeholders."""
    clean_run_root(output_root)
    inputs_config = json.loads(inputs_path.read_text(encoding="utf-8"))
    thumbnail_limit = inputs_config.get("channel_issues", {}).get("thumbnail-analysis-skill", {}).get("total_videos")
    normalized_input = normalize_channel_input(channel_input)
    run_root, collected = collect_configured(normalized_input, output_root, client, profile_path, thumbnail_limit)
    collection = json.loads((run_root / "normalized" / "collection.json").read_text(encoding="utf-8"))
    prepare_skill_inputs(run_dir=run_root, channel_data=collection["channel"],
                         recent_videos=collected["videos"], config_path=inputs_path,
                         collected=collected)
    prepare_skill_outputs(run_dir=run_root, config_path=inputs_path)
    return run_root, write_run_manifest(run_root)


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect a YouTube channel and prepare its Codex skill handoff.")
    parser.add_argument("channel", help="Channel URL, @handle, legacy URL, or channel ID")
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
        run_root, manifest_path = prepare_run(args.channel, Path(args.output),
                                              YouTubeClient(api_key, args.timeout),
                                              args.collection_config, args.inputs_config)
    except (ValueError, YouTubeAPIError, OSError, KeyError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"Run root: {run_root.resolve()}")
    print(f"Skill manifest: {manifest_path.resolve()}")
    print("Status: ready for Codex skills")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
