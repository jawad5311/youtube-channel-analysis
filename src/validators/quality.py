"""Quality gates for YouTube channel collection runs."""
from __future__ import annotations
from collections import Counter
from typing import Any

def build_quality_report(*, channel: dict[str, Any], playlist_video_ids: list[str], videos: list[dict[str, Any]], pagination_complete: bool) -> dict[str, Any]:
    retrieved_ids = [v.get("id") for v in videos if v.get("id")]
    duplicate_playlist = sorted(k for k, v in Counter(playlist_video_ids).items() if v > 1)
    duplicate_retrieved = sorted(k for k, v in Counter(retrieved_ids).items() if v > 1)
    missing = sorted(set(playlist_video_ids) - set(retrieved_ids))
    unexpected = sorted(set(retrieved_ids) - set(playlist_video_ids))
    errors: list[str] = []
    warnings: list[str] = []
    if not channel.get("id"): errors.append("Channel ID is missing.")
    if not pagination_complete: errors.append("Uploads pagination did not complete.")
    if duplicate_playlist: errors.append("Duplicate video IDs were present in the uploads playlist.")
    if duplicate_retrieved: errors.append("Duplicate video resources were retrieved.")
    if unexpected: errors.append("videos.list returned IDs that were not requested.")
    if missing: warnings.append("Some playlist videos were unavailable; they may be deleted or private.")
    total = len(set(playlist_video_ids))
    coverage = round(len(set(retrieved_ids)) / total * 100, 2) if total else 100.0
    return {"quality_passed": not errors, "pagination_complete": pagination_complete,
            "playlist_video_count": len(playlist_video_ids), "unique_playlist_video_count": total,
            "retrieved_video_count": len(retrieved_ids), "coverage_percent": coverage,
            "missing_video_ids": missing, "unexpected_video_ids": unexpected,
            "duplicate_playlist_video_ids": duplicate_playlist,
            "duplicate_retrieved_video_ids": duplicate_retrieved, "errors": errors, "warnings": warnings}
