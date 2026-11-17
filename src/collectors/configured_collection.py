"""Collect the configured fields, preserving uncertainty about Shorts."""
from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor
from urllib.request import Request, urlopen
from datetime import datetime, timezone
from pathlib import Path

from src.collectors.youtube_data_api import YouTubeAPIError, parse_channel_reference, slug, write_json

DEFAULT_PROFILE = Path(__file__).resolve().parents[2] / "config" / "quick-channel-collection.json"
CHANNEL_FIELDS = {"name": ("snippet", "title"), "description": ("snippet", "description"),
                  "tags": ("brandingSettings", "channel(keywords)"),
                  "country": ("snippet", "country"),
                  "subscriber_count": ("statistics", "subscriberCount"),
                  "branding_title": ("brandingSettings", "channel(title)"),
                  "branding_description": ("brandingSettings", "channel(description)"),
                  "topic_categories": ("topicDetails", "topicCategories"),
                  "banner_image": ("brandingSettings", "image(bannerExternalUrl)")}
VIDEO_FIELDS = {"title", "description", "tags", "publishedAt", "thumbnails", "liveBroadcastContent", "duration", "viewCount"}


def _collect_posts_http(channel_id: str, limit: int) -> dict:
    """Collect the initial public Posts page without scrolling."""
    url = f"https://www.youtube.com/channel/{channel_id}/posts?hl=en"
    request = Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "en-US,en;q=0.9"})
    with urlopen(request, timeout=30) as response:
        html = response.read().decode("utf-8", "ignore")
    match = re.search(r"var ytInitialData = (\{.*?\});", html)
    if not match:
        return {"status": "http_no_data", "posts": []}
    data = json.loads(match.group(1))
    posts, seen = [], set()

    def text(value):
        return "".join(item.get("text", "") for item in value.get("runs", []))

    def walk(value):
        if len(posts) >= limit:
            return
        if isinstance(value, dict):
            renderer = value.get("backstagePostRenderer")
            if renderer:
                post_id = renderer.get("postId")
                if post_id and post_id not in seen:
                    seen.add(post_id)
                    item = {"text": text(renderer.get("contentText", {})),
                            "publishedAt": text(renderer.get("publishedTimeText", {})),
                            "pinned": False, "postId": post_id}
                    posts.append(item)
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(data)
    return {"status": "complete" if posts else "http_no_posts", "posts": posts}


def _download_image(url: str | None, destination: Path) -> bool:
    if not url:
        return False
    try:
        request = Request(url, headers={"User-Agent": "youtube-channel-analysis/1.0"})
        with urlopen(request, timeout=20) as response:
            destination.write_bytes(response.read())
        return True
    except (OSError, ValueError):
        return False


def _download_thumbnail_assets(run_dir: Path, channel: dict, videos: list[dict], limit: int | None = None) -> dict:
    asset_dir = run_dir / "normalized" / "channel-issues" / "thumbnail-analysis"
    asset_dir.mkdir(parents=True, exist_ok=True)
    downloaded = {"banner": False, "videos": 0}
    banner_url = channel.get("brandingSettings", {}).get("image", {}).get("bannerExternalUrl")
    downloaded["banner"] = _download_image(banner_url, asset_dir / "banner.png")
    ordered = sorted(videos, key=lambda item: item.get("snippet", {}).get("publishedAt", ""), reverse=True)
    if limit is not None:
        ordered = ordered[:limit]
    for index, video in enumerate(ordered, start=1):
        thumbnails = video.get("snippet", {}).get("thumbnails", {})
        thumbnail = thumbnails.get("maxres") or thumbnails.get("standard") or thumbnails.get("high") or thumbnails.get("medium") or thumbnails.get("default")
        url = thumbnail.get("url") if isinstance(thumbnail, dict) else None
        if _download_image(url, asset_dir / f"video-{index}.png"):
            downloaded["videos"] += 1
    return downloaded


def project_video(item, fields):
    result = {}
    for field in fields:
        part = "contentDetails" if field == "duration" else "statistics" if field == "viewCount" else "snippet"
        if field in item.get(part, {}):
            result.setdefault(part, {})[field] = item[part][field]
    return result


def channel_selection(selected):
    groups = {}
    for part, field in selected:
        match = re.fullmatch(r"(\w+)\((\w+)\)", field)
        if match:
            groups.setdefault(part, {}).setdefault(match[1], {})[match[2]] = {}
        else:
            groups.setdefault(part, {})[field] = {}

    def render(tree):
        return ",".join(key + ("(" + render(value) + ")" if value else "")
                        for key, value in sorted(tree.items()))

    return [f"{part}({render(tree)})" for part, tree in groups.items()]


def load_profile(path: Path = DEFAULT_PROFILE) -> dict:
    profile = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(profile, dict) or set(profile) - {"channel", "videos", "shorts", "max_uploads_to_scan", "playlists", "community_posts", "activity_coverage"}:
        raise ValueError("Unsupported collection section.")
    if not isinstance(profile.get("channel", {}), dict):
        raise ValueError("channel must be an object.")
    for key, enabled in profile.get("channel", {}).items():
        if key not in CHANNEL_FIELDS or not isinstance(enabled, bool):
            raise ValueError(f"Unsupported channel setting: {key}")
    for section in ("videos", "shorts"):
        rule = profile.get(section, {})
        if not isinstance(rule, dict):
            raise ValueError(f"{section} must be an object.")
        limit = rule.get("limit", 0)
        if type(limit) is not int or limit < 0:
            raise ValueError(f"{section}.limit must be a nonnegative integer.")
        if set(rule) - {"limit", "fields"} or not isinstance(rule.get("fields", []), list):
            raise ValueError(f"Invalid {section} settings.")
        if set(rule.get("fields", [])) - VIDEO_FIELDS:
            raise ValueError(f"Unsupported {section} fields.")
    for section, allowed in (("playlists", {"playlistId", "playlistUrl", "title", "description", "itemCount"}),
                             ("community_posts", {"text", "publishedAt", "pinned"})):
        rule = profile.get(section, {})
        keys = {"enabled", "fields", "limit"} | ({"source"} if section == "community_posts" else set())
        if not isinstance(rule, dict) or set(rule) - keys:
            raise ValueError(f"Invalid {section} settings.")
        if type(rule.get("enabled", False)) is not bool:
            raise ValueError(f"Invalid {section}.enabled.")
        if not isinstance(rule.get("fields", []), list) or set(rule.get("fields", [])) - allowed:
            raise ValueError(f"Unsupported {section} fields.")
        if type(rule.get("limit", 0)) is not int or rule.get("limit", 0) < 0:
            raise ValueError(f"Invalid {section}.limit.")
    if profile.get("community_posts", {}).get("source", "browser") != "browser":
        raise ValueError("Community posts require browser collection.")
    coverage = profile.get("activity_coverage", {})
    if not isinstance(coverage, dict):
        raise ValueError("activity_coverage must be an object.")
    for key, value in coverage.items():
        if key in {"preferred_complete_weeks", "minimum_complete_weeks", "recent_days"}:
            if type(value) is not int or value < 1:
                raise ValueError(f"Invalid coverage setting: {key}")
        elif key in {"record_collection_date", "record_coverage_boundaries", "record_collection_status"}:
            if type(value) is not bool:
                raise ValueError(f"Invalid coverage setting: {key}")
        else:
            raise ValueError(f"Unsupported coverage setting: {key}")
    cap = profile.get("max_uploads_to_scan", 300)
    if type(cap) is not int or cap < 1:
        raise ValueError("max_uploads_to_scan must be a positive integer.")
    return profile


def collect_configured(channel_input, output_root, client, profile_path=DEFAULT_PROFILE, thumbnail_limit=None):
    profile = load_profile(profile_path)
    selected = [CHANNEL_FIELDS[key] for key, enabled in profile.get("channel", {}).items() if enabled]
    video_limit = profile.get("videos", {}).get("limit", 0)
    shorts_limit = profile.get("shorts", {}).get("limit", 0)
    parts = {part for part, _ in selected}
    selectors = channel_selection(selected)
    if profile.get("playlists", {}).get("enabled"):
        parts.add("statistics")
        selectors.append("statistics(videoCount)")
    if video_limit or shorts_limit:
        parts.add("contentDetails")
        selectors.append("contentDetails(relatedPlaylists(uploads))")
    ref = parse_channel_reference(channel_input)
    response = client.get("channels", part=",".join(sorted(parts)) or "id",
                          fields="items(id," + ",".join(selectors) + ")" if selectors else "items(id)",
                          **{ref.filter_name: ref.filter_value})
    if not response.get("items"):
        raise YouTubeAPIError("Channel not found.")
    channel = response["items"][0]
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    # Keep run folders stable by channel handle/ID rather than display name.
    folder_key = ref.filter_value.lstrip("@") if ref.filter_name == "forHandle" else channel["id"]
    # Handles are already constrained to a single URL path segment. Preserve
    # their spelling so the run folder matches the supplied channel handle.
    channel_dir = output_root / (folder_key if ref.filter_name == "forHandle" else slug(folder_key))
    channel_dir.mkdir(parents=True, exist_ok=True)
    versions = []
    for existing in channel_dir.iterdir():
        if existing.is_dir():
            match = re.match(r"^V(\d+)\s*-", existing.name, re.IGNORECASE)
            if match:
                versions.append(int(match.group(1)))
    version = max(versions, default=0) + 1
    run_dir = channel_dir / f"V{version} - {run_id}"
    write_json(run_dir / "raw/channel-response.json", response)
    community_rule = profile.get("community_posts", {})
    post_executor = ThreadPoolExecutor(max_workers=1) if community_rule.get("enabled") else None
    post_future = post_executor.submit(
        _collect_posts_http, channel["id"], community_rule.get("limit", 0)
    ) if post_executor else None
    videos, candidates, seen = [], [], set()
    token = None
    exhausted = False
    cap = profile.get("max_uploads_to_scan", 300)
    if profile.get("playlists", {}).get("enabled"):
        cap = max(cap, int(channel.get("statistics", {}).get("videoCount", 0) or 0))
    scanned, missing, unknown, dates = 0, 0, 0, []
    long_videos_scanned, shorts_scanned = 0, 0
    uploads = channel.get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads")
    if (video_limit or shorts_limit) and not uploads:
        raise YouTubeAPIError("Uploads playlist missing from channel response.")
    fields = sorted(set(profile.get("videos", {}).get("fields", [])) |
                    set(profile.get("shorts", {}).get("fields", [])))
    shorts_confirmed = False
    if shorts_limit and channel.get("id", "").startswith("UC"):
        shorts_playlist = "UUSH" + channel["id"][2:]
        fallback_candidates = candidates
        candidates = []
        shorts_token = None
        shorts_page = 0
        shorts_seen = set()
        try:
            while len(candidates) < shorts_limit:
                shorts_page += 1
                listing = client.get(
                    "playlistItems",
                    part="contentDetails",
                    playlistId=shorts_playlist,
                    fields="items(contentDetails(videoId)),nextPageToken",
                    maxResults=min(50, shorts_limit - len(candidates)),
                    pageToken=shorts_token,
                )
                write_json(run_dir / f"raw/shorts-uploads-{shorts_page:04}.json", listing)
                ids = [item["contentDetails"]["videoId"] for item in listing.get("items", [])]
                ids = [vid for vid in dict.fromkeys(ids) if vid not in shorts_seen]
                shorts_seen.update(ids)
                if not ids:
                    break
                selector = "id,contentDetails(duration)"
                snippet_fields = sorted((set(fields) - {"duration", "viewCount"}) | {"publishedAt"})
                if snippet_fields:
                    selector += ",snippet(" + ",".join(snippet_fields) + ")"
                parts = "contentDetails,snippet"
                if "viewCount" in fields:
                    selector += ",statistics(viewCount)"
                    parts += ",statistics"
                details = client.get("videos", part=parts,
                                     fields="items(" + selector + ")", id=",".join(ids))
                write_json(run_dir / f"raw/shorts-videos-{shorts_page:04}.json", details)
                by_id = {item["id"]: item for item in details.get("items", [])}
                for vid in ids:
                    item = by_id.get(vid)
                    if item:
                        duration_match = re.fullmatch(
                            r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?",
                            item.get("contentDetails", {}).get("duration", ""),
                        )
                        if not duration_match:
                            continue
                        hours, minutes, seconds = (float(value or 0) for value in duration_match.groups())
                        duration = hours * 3600 + minutes * 60 + seconds
                        if 0 < duration <= 180:
                            candidates.append(project_video(item, profile.get("shorts", {}).get("fields", [])))
                        if len(candidates) >= shorts_limit:
                            break
                shorts_token = listing.get("nextPageToken")
                if not shorts_token:
                    break
            shorts_confirmed = bool(candidates)
        except YouTubeAPIError:
            shorts_confirmed = False
            candidates = fallback_candidates[:shorts_limit]
    page = 0
    while (video_limit or shorts_limit) and scanned < cap:
        page += 1
        listing = client.get("playlistItems", part="contentDetails", playlistId=uploads,
                             fields="items(contentDetails(videoId)),nextPageToken",
                             maxResults=min(50, cap - scanned), pageToken=token)
        write_json(run_dir / f"raw/uploads-{page:04}.json", listing)
        entries = listing.get("items", [])[:cap - scanned]
        scanned += len(entries)
        ids = [item["contentDetails"]["videoId"] for item in entries]
        ids = list(dict.fromkeys(vid for vid in ids if vid not in seen))
        seen.update(ids)
        if ids:
            selector = "id,contentDetails(duration)"
            snippet_fields = sorted((set(fields) - {"duration", "viewCount"}) | {"publishedAt"})
            if snippet_fields:
                selector += ",snippet(" + ",".join(snippet_fields) + ")"
            video_parts = "contentDetails,snippet"
            if "viewCount" in fields:
                selector += ",statistics(viewCount)"
                video_parts += ",statistics"
            details = client.get("videos", part=video_parts,
                                 fields="items(" + selector + ")", id=",".join(ids))
            write_json(run_dir / f"raw/videos-{page:04}.json", details)
            by_id = {v["id"]: v for v in details.get("items", [])}
            for vid in ids:
                item = by_id.get(vid)
                if not item:
                    missing += 1
                    continue
                if item.get("snippet", {}).get("publishedAt"):
                    dates.append(item["snippet"]["publishedAt"])
                match = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?", item.get("contentDetails", {}).get("duration", ""))
                if not match:
                    unknown += 1
                    continue
                hours, minutes, seconds = (float(x or 0) for x in match.groups())
                duration = hours * 3600 + minutes * 60 + seconds
                if duration <= 0:
                    unknown += 1
                    continue
                section = "videos" if duration > 180 else "shorts"
                if section == "videos":
                    long_videos_scanned += 1
                else:
                    shorts_scanned += 1
                target = videos if section == "videos" else candidates
                if section == "shorts" and shorts_confirmed:
                    continue
                section_limit = video_limit if section == "videos" else shorts_limit
                if len(target) < section_limit:
                    target.append(project_video(item, profile.get(section, {}).get("fields", [])))
        token = listing.get("nextPageToken")
        if not token:
            exhausted = True
            break
        if not ids:
            break
    playlists, playlist_status = [], "disabled"
    rule = profile.get("playlists", {})
    if rule.get("enabled"):
        playlist_status, token, page = "complete", None, 0
        pfields = rule.get("fields", [])
        snippet = [f for f in pfields if f not in {"playlistId", "playlistUrl", "itemCount"}]
        selectors = ["id", "status(privacyStatus)"]
        pparts = ["status"]
        if snippet:
            selectors.append("snippet(" + ",".join(snippet) + ")")
            pparts.append("snippet")
        if "itemCount" in pfields:
            selectors.append("contentDetails(itemCount)")
            pparts.append("contentDetails")
        while True:
            page += 1
            response = client.get("playlists", part=",".join(pparts), channelId=channel["id"],
                                  fields="items(" + ",".join(selectors) + "),nextPageToken",
                                  maxResults=50, pageToken=token)
            write_json(run_dir / f"raw/playlists-{page:04}.json", response)
            for item in response.get("items", []):
                if item.get("status", {}).get("privacyStatus") == "public":
                    playlist = {}
                    for field in pfields:
                        if field == "playlistId":
                            playlist[field] = item.get("id")
                        elif field == "playlistUrl":
                            playlist[field] = f"https://www.youtube.com/playlist?list={item.get('id')}"
                        else:
                            playlist[field] = item.get("contentDetails" if field == "itemCount" else "snippet", {}).get(field)
                    playlists.append(playlist)
            next_token = response.get("nextPageToken")
            if not next_token:
                break
            if next_token == token:
                playlist_status = "partial"
                break
            token = next_token
    if post_future:
        try:
            community = post_future.result()
        except (OSError, ValueError, json.JSONDecodeError, TimeoutError) as exc:
            community = {"status": "http_failed", "posts": [], "error": str(exc)}
        post_executor.shutdown(wait=True)
    else:
        community = {"status": "disabled", "posts": []}
    coverage = profile.get("activity_coverage", {})
    if community_rule.get("enabled") and community["status"] != "complete":
        write_json(run_dir / "browser-collection-request.json", {
            "channel_url": f"https://www.youtube.com/channel/{channel['id']}/posts",
            "community_posts": community_rule, "activity_coverage": coverage,
            "instruction": "HTTP collection did not produce posts. Collect with a browser and save posts in normalized/community-posts.json.",
        })
    metadata = {"shorts_confirmed": shorts_confirmed, "uploads_scanned": scanned,
                "total_long_videos_scanned": long_videos_scanned,
                "total_shorts_scanned": shorts_scanned,
                "uploads_exhausted": exhausted, "missing_videos": missing, "unknown_durations": unknown,
                "scan_limit_reached": scanned >= cap,
                "requested_counts": {"videos": video_limit, "shorts": shorts_limit},
                "coverage_requirements": coverage}
    if coverage.get("record_collection_date"):
        metadata["collected_at"] = datetime.now(timezone.utc).isoformat()
    if coverage.get("record_coverage_boundaries"):
        metadata["coverage"] = {"oldest_observed": min(dates) if dates else None,
                                "newest_observed": max(dates) if dates else None,
                                "complete_history": exhausted and not missing and not unknown}
    if coverage.get("record_collection_status"):
        metadata["status"] = "partial" if shorts_limit or missing or unknown or community_rule.get("enabled") or len(videos) < video_limit else "ready"
    result = {"channel": channel, "videos": videos, "shorts_candidates": candidates,
              "total_public_videos": channel.get("statistics", {}).get("videoCount", 0),
              "total_long_videos": long_videos_scanned,
              "total_shorts": shorts_scanned,
              "total_videos_retrieved": len(videos), "total_shorts_retrieved": len(candidates),
              "playlists": playlists, "playlist_status": playlist_status,
              "community_posts": community, "collection_metadata": metadata}
    result["thumbnail_assets"] = _download_thumbnail_assets(run_dir, channel, videos, thumbnail_limit)
    write_json(run_dir / "normalized/collection.json", {"collection_scope": "configured_channel", "requested_input": channel_input, **result})
    write_json(run_dir / "normalized/recent-videos.json", {"total_videos_retrieved": len(videos), "videos": videos})
    write_json(run_dir / "normalized/shorts-candidates.json", {"total_shorts_retrieved": len(candidates), "videos": candidates,
               "classification": "Unconfirmed: duration at most 180 seconds; API does not expose Shorts status."})
    write_json(run_dir / "collection-profile.json", profile)
    write_json(run_dir / "normalized/playlists.json", {"status": playlist_status, "playlists": playlists})
    write_json(run_dir / "normalized/community-posts.json", community)
    write_json(run_dir / "manifest.json", {"status": "partial" if shorts_limit or len(videos) < video_limit or community_rule.get("enabled") or missing or unknown else "ready",
               "videos_retrieved": len(videos), "shorts_retrieved": len(candidates),
               "uploads_scanned": scanned, "uploads_exhausted": exhausted, "api_requests": client.request_count,
               "playlist_status": playlist_status, "community_status": community["status"],
               "missing_videos": missing, "unknown_durations": unknown,
               "limitations": ["Shorts require confirmation; short landscape videos may be candidates and are excluded from videos."] if shorts_limit or video_limit else []})
    return run_dir, result
