---
name: quick-channel-analysis
description: Run this project's metadata-only quick YouTube channel analysis for a channel URL, handle, or channel ID. Use for niche, category, and metadata-level issue summaries; not for full channel audits.
---

# Quick Channel Analysis

Use this skill when the user wants a fast YouTube channel assessment with channel niches, a primary category, and metadata-level channel issues.

The project workflow is the source of truth. From the YouTube analysis project root, run:

```powershell
python -m src.workflows.quick_channel_analysis <channel>
```

Replace `<channel>` with a YouTube channel URL, `@handle`, legacy username URL, or UC channel ID. The workflow uses the shared metadata collector and creates a text report plus structured JSON under `runs/<channel>/<run-id>/`.

Use the `$find-channel-niches` skill on the collected channel information to determine the niche. Follow that skill's broad-niche and strict output rules internally, then place its result in the `niche` field below.

For a single-channel quick report, return exactly these fields:

```text
channel name:
<channel name>

channel url:
<channel URL>

channel category:
<broad content category>

current subscribers:
<subscriber count>

niche:
<niche result from $find-channel-niches>

country:
<full readable country name>

channel issues:
<issue text or No metadata-level channel issues were found.>
```

For now, report metadata-level issues only. Later issue-specific skills may expand the `channel issues` section. State that the quick analysis does not assess videos, thumbnails, playlists, recent activity, or community posts.
Do not substitute the full-audit workflow or infer video-level issues. If API collection fails, report the error and do not fabricate an analysis.
