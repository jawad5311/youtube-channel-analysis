---
name: youtube-channel-analysis--quick
description: Orchestrate a quick YouTube channel analysis from one channel URL or handle and return a concise client-ready result.
---

# Quick YouTube Channel Analysis Orchestrator

Use this skill when the user invokes the quick channel analysis workflow for one YouTube channel. Accept a YouTube channel URL, `@handle`, legacy username URL, or channel ID.

## Workflow

1. Normalize the channel input and preserve the canonical channel URL.
2. Run the project's shared metadata collector:

   ```powershell
   python -m src.workflows.quick_channel_analysis <channel>
   ```

3. Read the collected channel metadata and the generated structured analysis.
4. Use `$find-channel-niches` on the collected channel information and place its result in the `niche` field.
5. Use `youtube-channel-categorization` when the CRM category is required. Keep CRM category separate from the broad content category.
6. Run issue-specific skills only when their required evidence has been collected. Current optional quick checks are:
   - `check-video-seo-score` for recent video metadata and descriptions.
   - `analyze-shorts-activity` for Shorts publication dates.
   - `analyze-playlists` for public playlist data.
   - `analyze-community-activity` for the channel Posts page.
7. Combine the results into one quick analysis. Do not invent findings when a collector or browser check fails; report insufficient data for that specific check.

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
