"""Metadata-only analysis used by the quick channel workflow."""
from __future__ import annotations

import re
from typing import Any

from iso3166 import countries


CATEGORY_KEYWORDS = {
    "Health": ("health", "medical", "medicine", "disease", "wellness", "nutrition", "fitness", "kidney"),
    "Technology": ("technology", "software", "coding", "programming", "ai", "artificial intelligence"),
    "Business": ("business", "entrepreneur", "leadership", "sales", "startup"),
    "Education": ("education", "learning", "teaching", "course", "tutorial", "explained"),
    "Finance": ("finance", "investing", "stocks", "banking", "cryptocurrency", "money"),
    "Marketing": ("marketing", "seo", "advertising", "branding", "social media"),
    "Food": ("food", "cooking", "recipe", "kitchen", "baking"),
    "Travel": ("travel", "trip", "tourism", "destination", "hotel"),
    "Gaming": ("gaming", "gameplay", "games", "minecraft", "esports"),
}


def _text_for_classification(channel: dict[str, Any]) -> str:
    snippet = channel.get("snippet", {})
    branding = channel.get("brandingSettings", {}).get("channel", {})
    topics = channel.get("topicDetails", {}).get("topicCategories", [])
    return " ".join(
        str(value)
        for value in (
            snippet.get("title", ""),
            snippet.get("description", ""),
            branding.get("keywords", ""),
            " ".join(topics),
        )
    ).lower()


def classify_niches(channel: dict[str, Any]) -> list[str]:
    """Return up to three broad, metadata-supported niche candidates."""
    text = _text_for_classification(channel)
    scores = {
        category: sum(len(re.findall(rf"(?<!\\w){re.escape(keyword)}(?!\\w)", text)) for keyword in keywords)
        for category, keywords in CATEGORY_KEYWORDS.items()
    }
    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    top_score = ranked[0][1] if ranked else 0
    return [
        category
        for index, (category, score) in enumerate(ranked)
        if score >= 2 and (index == 0 or (score >= 3 and score >= top_score * 0.15))
    ][:3]


def find_channel_issues(channel: dict[str, Any]) -> list[str]:
    """Identify actionable metadata problems, not video-level audit findings."""
    snippet = channel.get("snippet", {})
    branding = channel.get("brandingSettings", {}).get("channel", {})
    issues: list[str] = []

    description = snippet.get("description", "").strip()
    if not description:
        issues.append("The channel About description is missing.")
    elif len(description) < 120:
        issues.append("The channel About description is too short to clearly establish positioning.")
    if not branding.get("keywords", "").strip():
        issues.append("Channel keywords are missing, limiting metadata-based discoverability signals.")
    if not snippet.get("country"):
        issues.append("The channel country is not set.")
    if not channel.get("topicDetails", {}).get("topicCategories"):
        issues.append("YouTube has not assigned topic categories to the channel.")
    return issues

def readable_country(code: str | None) -> str:
    if not code:
        return "Not specified"
    try:
        return countries.get(code.upper()).name
    except KeyError:
        return code.upper()

def analyze_quick_channel(collection: dict[str, Any]) -> dict[str, Any]:
    """Create the portable quick-analysis result from a metadata collection."""
    channel = collection["channel"]
    snippet = channel.get("snippet", {})
    statistics = channel.get("statistics", {})
    branding = channel.get("brandingSettings", {}).get("channel", {})
    niches = classify_niches(channel)
    category = niches[0] if niches else "Unclear"
    issues = find_channel_issues(channel)
    return {
        "schema_version": "0.1.0",
        "analysis_type": "quick_channel_analysis",
        "collection_scope": collection.get("collection_scope"),
        "channel_id": channel.get("id"),
        "channel_name": snippet.get("title"),
        "channel_url": collection.get("requested_input"),
        "current_subscribers": statistics.get("subscriberCount"),
        "country": readable_country(snippet.get("country") or branding.get("country")),
        "channel_niches": niches or ["Unclear"],
        "channel_category": category,
        "channel_issues": issues,
        "scope_note": (
            "This quick analysis uses channel metadata only. It does not assess videos, thumbnails, "
            "recent activity, playlists, or community posts."
        ),
    }


def render_quick_analysis(analysis: dict[str, Any]) -> str:
    issues = analysis["channel_issues"] or ["No metadata-level channel issues were found."]
    subscribers = analysis["current_subscribers"]
    lines = [
        "channel name:",
        analysis["channel_name"] or "Not specified",
        "",
        "channel url:",
        analysis["channel_url"] or "Not specified",
        "",
        "channel category:",
        analysis["channel_category"],
        "",
        "current subscribers:",
        f"{int(subscribers):,}" if subscribers else "Not publicly displayed",
        "",
        "niche:",
        ", ".join(analysis["channel_niches"]),
        "",
        "country:",
        analysis["country"],
        "",
        "channel issues:",
        *issues,
    ]
    return "\n".join(lines) + "\n"
