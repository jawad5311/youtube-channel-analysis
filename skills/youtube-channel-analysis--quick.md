---
name: youtube-channel-analysis--quick
description: Orchestrate a quick YouTube channel analysis from one channel URL or handle and return a concise client-ready result.
---

# Quick YouTube Channel Analysis Orchestrator

Use this skill when the user invokes the quick channel analysis workflow for one YouTube channel. Accept a YouTube channel URL, `@handle`, legacy username URL, or channel ID.

## Workflow

1. When a channel URL or handle is received, format it into a valid YouTube channel reference and preserve the canonical channel URL.
2. Request the channel metadata from the YouTube Data API through the project's shared collector:

   ```powershell
   python -m src.workflows.quick_channel_analysis <channel>
   ```

3. Wait for the complete API response and confirm that all requested channel data has been received before starting analysis. Do not analyze partial or incomplete data.
4. Read the collected channel metadata and the generated structured analysis.
5. Use `$find-channel-niches` on the collected channel information and place its result in the `niche` field.
6. Use `youtube-channel-categorization` when the CRM category is required. Keep CRM category separate from the broad content category.
7. Run issue-specific skills only when their required evidence has been collected. Current optional quick checks are:
   - `check-video-seo-score` for recent video metadata and descriptions.
   - `analyze-shorts-activity` for Shorts publication dates.
   - `analyze-playlists` for public playlist data.
   - `analyze-community-activity` for the channel Posts page.
8. Combine the results into one quick analysis. Do not invent findings when a collector or browser check fails; report insufficient data for that specific check.

## Required field mapping

The quick workflow must produce these fields in this order:

```text
channel name:
<channel name>

channel url:
<canonical channel URL>

channel category:
<broad content category>

current subscribers:
<subscriber count>

niche:
<niche result from $find-channel-niches>

country:
<full readable country name>

channel issues:
<combined concise issue text>
```

Use the collected channel metadata as follows:

- `channel name`: `snippet.title`.
- `channel url`: the normalized canonical URL resolved from the input.
- `channel category`: the broad content category inferred from the channel title, description, keywords, topic IDs, and topic categories.
- `current subscribers`: `statistics.subscriberCount`, formatted as a readable number.
- `niche`: the exact comma-separated result from `$find-channel-niches`.
- `country`: convert `snippet.country` to the full readable country name. Do not return the two-letter country code.
- `channel issues`: combine only supported metadata and completed specialist findings into concise text.

When running `$find-channel-niches`, provide the channel title, About description, channel keywords, topic IDs, topic categories, and any available representative video titles or descriptions. Follow that skill's exact comma-separated output rules and place the result directly in the `niche` field without adding a label or explanation.

## Output

Return exactly this compact format for a single channel:

```text
channel name:
<channel name>

channel url:
<canonical channel URL>

channel category:
<broad content category>

current subscribers:
<subscriber count>

niche:
<niche result from $find-channel-niches>

country:
<full readable country name>

channel issues:
<combined concise issue text>
```

The `channel issues` value should include only actionable findings supported by the available evidence. If no metadata-level issue is found and no optional issue check has produced a finding, use:

```text
No channel issues were found.
```

Keep the quick result concise. Do not include detailed per-video findings, raw API payloads, audit recommendations, thumbnail analysis, PDF generation, or a full web report. Those belong to the full audit workflow.

## Failure handling

- If channel collection fails, return the collection error and do not fabricate an analysis.
- If an optional issue check lacks its required evidence, omit that check from the combined result rather than guessing.
- Preserve the successful channel fields when only an optional check fails.
- When Google Sheets integration is enabled, match the row by normalized channel URL or channel ID, update the existing row, and report duplicate or missing matches without silently overwriting or creating a row.
