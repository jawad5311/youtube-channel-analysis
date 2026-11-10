"""Prepare and validate the channel-categorization skill handoff."""
from __future__ import annotations

import json
from pathlib import Path


ALLOWED_CATEGORIES = frozenset({"Business", "Healthcare", "Education", "Creator"})


def load_categorization_input(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    required = {"channel_name", "channel_description", "videos"}
    missing = sorted(required - set(data))
    if missing:
        raise ValueError(f"Categorization input is missing: {', '.join(missing)}")
    if not isinstance(data["videos"], list):
        raise ValueError("Categorization videos must be a list.")
    return data


def validate_category_result(result: str) -> str:
    """Accept only the exact one-line category required by the skill."""
    category = result.strip()
    if category not in ALLOWED_CATEGORIES:
        raise ValueError("Categorization result must be exactly Business, Healthcare, Education, or Creator.")
    return category


def build_categorization_request(input_path: Path, skill_path: Path) -> dict:
    """Describe the handoff that ChatGPT/the orchestrator must execute."""
    load_categorization_input(input_path)
    return {
        "skill": "youtube-channel-categorization",
        "skill_instructions": str(skill_path),
        "input_file": str(input_path),
        "output_contract": "Return exactly one label: Business, Healthcare, Education, or Creator.",
    }


def save_category_result(run_dir: Path, result: str) -> Path:
    """Save a validated skill result for inspection and later synthesis."""
    category = validate_category_result(result)
    output_dir = run_dir / "analysis"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "channel-categorization.json"
    output_path.write_text(json.dumps({
        "skill": "youtube-channel-categorization",
        "category": category,
        "status": "success",
    }, indent=2), encoding="utf-8")
    (output_dir / "channel-categorization.txt").write_text(category + "\n", encoding="utf-8")
    return output_path
