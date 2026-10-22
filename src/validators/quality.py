"""Quality gates for YouTube channel metadata collection runs."""
from __future__ import annotations
from typing import Any

def build_quality_report(*, channel: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if not channel.get("id"): errors.append("Channel ID is missing.")
    if not channel.get("snippet", {}).get("title"): warnings.append("Channel title is missing.")
    return {
        "quality_passed": not errors,
        "collection_scope": "channel_metadata",
        "errors": errors,
        "warnings": warnings,
    }
