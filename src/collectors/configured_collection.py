"""Collect the configured fields, preserving uncertainty about Shorts."""
from __future__ import annotations

import json
import re
import shutil
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


def _channel_tabs_from_html(html: str, channel_id: str) -> dict:
    match = re.search(r"var ytInitialData\s*=\s*", html)
    if not match:
        return {"status": "unavailable", "tabs": []}
    data, _ = json.JSONDecoder().raw_decode(html, match.end())
    metadata = data.get("metadata", {}).get("channelMetadataRenderer", {})
    if metadata.get("externalId") != channel_id:
        return {"status": "unavailable", "tabs": []}
    entries = data.get("contents", {}).get("twoColumnBrowseResultsRenderer", {}).get("tabs", [])
    tabs = []
    for entry in entries:
        tab = entry.get("tabRenderer", {})
        title = tab.get("title")
        if title:
            tabs.append({"name": title, "selected": bool(tab.get("selected"))})
    return {"status": "complete" if tabs else "unavailable", "tabs": tabs}


def _collect_channel_tabs(channel_id: str, run_dir: Path) -> dict:
    url = f"https://www.youtube.com/channel/{channel_id}?hl=en"
    try:
        request = Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "en-US,en;q=0.9"})
        with urlopen(request, timeout=15) as response:
            html = response.read().decode("utf-8", "replace")
        (run_dir / "raw" / "channel-page.html").write_text(html, encoding="utf-8")
        result = _channel_tabs_from_html(html, channel_id)
    except (OSError, ValueError, TypeError, AttributeError):
        result = {"status": "unavailable", "tabs": []}
    result["source_url"] = url
    write_json(run_dir / "normalized" / "channel-tabs.json", result)
    return result


def _collect_posts_http(posts_url: str, limit: int) -> dict:
    """Collect the initial public Posts page without scrolling."""
    request = Request(f"{posts_url}?hl=en", headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "en-US,en;q=0.9"})
    with urlopen(request, timeout=30) as response:
        html = response.read().decode("utf-8", "ignore")
    match = re.search(r"var ytInitialData = (\{.*?\});", html)
    if not match:
        return {"status": "http_no_data", "posts": []}
    data = json.loads(match.group(1))
    contents = data.get("contents")
    if not isinstance(contents, dict):
        return {"status": "http_no_data", "posts": []}
    tabs = contents.get("twoColumnBrowseResultsRenderer", {}).get("tabs", [])
    posts_tab = None
    for entry in tabs:
        tab = entry.get("tabRenderer", {})
        endpoint = tab.get("endpoint", {}).get("commandMetadata", {}).get("webCommandMetadata", {}).get("url", "")
        if tab.get("selected") and (tab.get("title", "").strip().casefold() == "posts" or endpoint.rstrip("/").endswith("/posts")):
            posts_tab = tab
            break
    if posts_tab is None:
        return {"status": "http_no_data", "posts": []}
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

    walk(posts_tab.get("content", {}))
    return {"status": "complete" if posts else "http_no_posts", "posts": posts}


def _shorts_page_ids(html: str, limit: int) -> tuple[list[str], str]:
    match = re.search(r"var ytInitialData\s*=\s*", html)
    if not match:
        return [], "unavailable"
    data, _ = json.JSONDecoder().raw_decode(html, match.end())
    tabs = data.get("contents", {}).get("twoColumnBrowseResultsRenderer", {}).get("tabs", [])
    selected = next((e.get("tabRenderer", {}) for e in tabs if e.get("tabRenderer", {}).get("selected")), {})
    titles = [e.get("tabRenderer", {}).get("title", "").casefold() for e in tabs]
    if selected.get("title", "").casefold() != "shorts":
        if selected.get("title", "").casefold() == "home" and "videos" in titles and "shorts" not in titles:
            return [], "no_visible_shorts"
        return [], "unavailable"
    content = selected.get("content")
    if not isinstance(content, dict):
        return [], "unavailable"
    ids = {}
    def walk(node):
        if isinstance(node, dict):
            item = node.get("shortsLockupViewModel", {})
            endpoint = item.get("onTap", {}).get("innertubeCommand", {}).get("reelWatchEndpoint", {})
            vid = endpoint.get("videoId", "") or item.get("entityId", "").removeprefix("shorts-shelf-item-")
            if re.fullmatch(r"[A-Za-z0-9_-]{11}", vid): ids[vid] = None
            for value in node.values(): walk(value)
        elif isinstance(node, list):
            for value in node: walk(value)
    walk(content)
    if ids: return list(ids)[:limit], "complete"
    return [], "unavailable"


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


def _videos_tab_ids(html: str, limit: int | None = None) -> list[str]:
    match = re.search(r"var ytInitialData\s*=\s*", html)
    if not match:
        return []
    data, _ = json.JSONDecoder().raw_decode(html, match.end())
    tabs = data.get("contents", {}).get("twoColumnBrowseResultsRenderer", {}).get("tabs", [])
    for entry in tabs:
        tab = entry.get("tabRenderer", {})
        if tab.get("selected") and tab.get("title") == "Videos":
            grid = tab.get("content", {}).get("richGridRenderer", {}).get("contents", [])
            break
    else:
        return []

    ids = {}
    for entry in grid:
        item = entry.get("richItemRenderer", {}).get("content", {})
        video_id = item.get("videoRenderer", {}).get("videoId", "")
        lockup = item.get("lockupViewModel", {})
        if lockup.get("contentType") == "LOCKUP_CONTENT_TYPE_VIDEO":
            video_id = lockup.get("contentId", "")
        if re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
            ids[video_id] = None
            if limit is not None and len(ids) == limit:
                break
    return list(ids)


def _collect_thumbnail_videos(client, channel_id: str, records: dict, limit: int, run_dir: Path | None = None) -> tuple[list[dict], str]:
    url = f"https://www.youtube.com/channel/{channel_id}/videos?hl=en"
    request = Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "en-US,en;q=0.9"})
    try:
        with urlopen(request, timeout=15) as response:
            html = response.read().decode("utf-8", "replace")
        if run_dir is not None:
            (run_dir / "raw" / "videos-page.html").write_text(html, encoding="utf-8")
        all_ids = _videos_tab_ids(html)
        if run_dir is not None:
            write_json(run_dir / "normalized" / "videos-page-ids.json", {"source_url": url, "video_ids": all_ids})
        ids = all_ids[:limit]
    except (OSError, ValueError):
        return [], "videos_tab_unavailable"
    if not ids:
        return [], "no_verified_videos"

    missing = [video_id for video_id in ids if not records.get(video_id, {}).get("snippet", {}).get("thumbnails")]
    for start in range(0, len(missing), 50):
        try:
            details = client.get("videos", part="snippet", fields="items(id,snippet(channelId,thumbnails))",
                                 id=",".join(missing[start:start + 50]))
        except YouTubeAPIError:
            break
        records.update({item["id"]: item for item in details.get("items", [])
                        if item.get("snippet", {}).get("channelId") == channel_id})
    return [records[video_id] for video_id in ids if video_id in records], "videos_tab"


def _download_thumbnail_assets(run_dir: Path, channel: dict, videos: list[dict]) -> dict:
    asset_dir = run_dir / "normalized" / "channel-issues" / "thumbnail-analysis"
    asset_dir.mkdir(parents=True, exist_ok=True)
    downloaded = {"banner": False, "videos": 0}
    banner_url = channel.get("brandingSettings", {}).get("image", {}).get("bannerExternalUrl")
    downloaded["banner"] = _download_image(banner_url, asset_dir / "banner.png")
    for video in videos:
        thumbnails = video.get("snippet", {}).get("thumbnails", {})
        thumbnail = thumbnails.get("maxres") or thumbnails.get("standard") or thumbnails.get("high") or thumbnails.get("medium") or thumbnails.get("default")
        url = thumbnail.get("url") if isinstance(thumbnail, dict) else None
        if _download_image(url, asset_dir / f"video-{downloaded['videos'] + 1}.png"):
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
    root = output_root.expanduser().resolve()
    if channel_dir.is_symlink() or channel_dir.resolve().parent != root:
        raise ValueError("Invalid channel run folder.")
    if channel_dir.exists():
        shutil.rmtree(channel_dir)
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
    channel_tabs = _collect_channel_tabs(channel["id"], run_dir)
    community_rule = profile.get("community_posts", {})
    posts_url = (f"https://www.youtube.com/{ref.filter_value}/posts" if ref.filter_name == "forHandle"
                 else f"https://www.youtube.com/channel/{channel['id']}/posts")
    post_executor = ThreadPoolExecutor(max_workers=1) if community_rule.get("enabled") else None
    post_future = post_executor.submit(
        _collect_posts_http, posts_url, community_rule.get("limit", 0)
    ) if post_executor else None
    videos, candidates, seen = [], [], set()
    thumbnail_records = {}
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
    shorts_status = "not_requested" if not shorts_limit else "unavailable"
    candidates = []
    if shorts_limit:
        url = f"https://www.youtube.com/channel/{channel['id']}/shorts?hl=en"
        try:
            request = Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "en-US,en;q=0.9"})
            with urlopen(request, timeout=15) as response:
                html = response.read().decode("utf-8", "replace")
            (run_dir / "raw" / "shorts-page.html").write_text(html, encoding="utf-8")
            shorts_ids, shorts_status = _shorts_page_ids(html, shorts_limit)
            page_tabs = _channel_tabs_from_html(html, channel["id"])
            if page_tabs["status"] != "complete":
                shorts_ids, shorts_status = [], "unavailable"
            elif shorts_status == "unavailable" and channel_tabs["status"] == "complete":
                names = {tab["name"].casefold() for tab in channel_tabs["tabs"]}
                selected_tabs = {tab["name"].casefold() for tab in page_tabs["tabs"] if tab["selected"]}
                if "shorts" not in names and selected_tabs.intersection({"home", "videos"}):
                    shorts_status = "no_visible_shorts"
            write_json(run_dir / "normalized" / "shorts-page-ids.json", {"source_url": url, "video_ids": shorts_ids, "status": shorts_status})
            if shorts_ids:
                details = client.get("videos", part="snippet,contentDetails,statistics", id=",".join(shorts_ids))
                write_json(run_dir / "raw" / "shorts-videos-0001.json", details)
                by_id = {v["id"]: v for v in details.get("items", []) if v.get("snippet", {}).get("channelId") == channel["id"]}
                if len(by_id) != len(shorts_ids):
                    shorts_status = "unavailable"
                else:
                    candidates = [project_video(by_id[vid], profile.get("shorts", {}).get("fields", [])) for vid in shorts_ids]
                    shorts_confirmed = True
        except (OSError, ValueError, YouTubeAPIError):
            shorts_status = "unavailable"
            candidates = []
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
            if thumbnail_limit:
                thumbnail_records.update(by_id)
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
                if section == "shorts":
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
            "channel_url": posts_url,
            "community_posts": community_rule, "activity_coverage": coverage,
            "instruction": "HTTP collection did not verify Posts-tab posts. Inspect the channel's /posts page in a browser only; do not use the separate /community feed. Save the result in normalized/community-posts.json.",
        })
    metadata = {"shorts_confirmed": shorts_confirmed, "shorts_status": shorts_status, "channel_tabs_status": channel_tabs["status"], "uploads_scanned": scanned,
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
    result = {"channel": channel, "channel_tabs": channel_tabs, "videos": videos, "shorts_candidates": candidates,
              "total_public_videos": channel.get("statistics", {}).get("videoCount", 0),
              "total_long_videos": long_videos_scanned,
              "total_shorts": shorts_scanned,
              "total_videos_retrieved": len(videos), "total_shorts_retrieved": len(candidates),
              "playlists": playlists, "playlist_status": playlist_status,
              "community_posts": community, "collection_metadata": metadata}
    thumbnail_videos, thumbnail_status = [], "not_requested"
    if thumbnail_limit:
        thumbnail_videos, thumbnail_status = _collect_thumbnail_videos(client, channel["id"], thumbnail_records,
                                                                       thumbnail_limit, run_dir)
        if thumbnail_status == "videos_tab_unavailable":
            thumbnail_videos = sorted(videos, key=lambda video: video.get("snippet", {}).get("publishedAt", ""),
                                      reverse=True)[:thumbnail_limit]
            thumbnail_status = "api_duration_fallback"
    result["thumbnail_assets"] = _download_thumbnail_assets(run_dir, channel, thumbnail_videos)
    result["thumbnail_assets"]["source_status"] = thumbnail_status
    ids_file = run_dir / "normalized" / "videos-page-ids.json"
    if ids_file.exists():
        performance_ids = json.loads(ids_file.read_text(encoding="utf-8"))["video_ids"][:20]
        if performance_ids:
            performance_response = client.get(
                "videos", part="snippet,statistics",
                fields="items(id,snippet(channelId,title,publishedAt),statistics(viewCount))",
                id=",".join(performance_ids),
            )
            write_json(run_dir / "raw" / "performance-videos.json", performance_response)
            indexed = {item["id"]: item for item in performance_response.get("items", [])
                       if item.get("snippet", {}).get("channelId") == channel["id"]}
            result["performance_videos"] = [indexed[video_id] for video_id in performance_ids if video_id in indexed]
            result["performance_missing_video_ids"] = [video_id for video_id in performance_ids if video_id not in indexed]
    write_json(run_dir / "normalized/collection.json", {"collection_scope": "configured_channel", "requested_input": channel_input, **result})
    write_json(run_dir / "normalized/recent-videos.json", {"total_videos_retrieved": len(videos), "videos": videos})
    write_json(run_dir / "normalized/shorts-candidates.json", {"total_shorts_retrieved": len(candidates), "videos": candidates,
               "classification": "Shorts tab IDs" if shorts_confirmed else shorts_status})
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
