---
name: quick-channel-analysis
description: Run a quick YouTube channel analysis directly from a channel URL, @handle, legacy username URL, or channel ID and return a concise client-ready result.
---

# Quick YouTube Channel Analysis Orchestrator

Use this skill as the direct entry point when the user provides one YouTube channel URL, `@handle`, legacy username URL, or channel ID. The supplied channel value is the workflow input.

## Workflow

1. Normalize the supplied channel input before collection. Accept a full YouTube URL, `youtube.com/@handle`, an `@handle`, a legacy username URL, or a channel ID. Remove tab paths such as `/videos`, `/shorts`, `/about`, `/featured`, `/live`, `/streams`, `/community`, and `/playlists` from URLs. Pass the normalized reference to the project's data-fetching workflow, while preserving the canonical display URL as `youtube.com/@handle` when a handle is available.

2. Request the channel metadata from the YouTube Data API through the project's shared collector:

   ```powershell
   python orchestrator.py <channel>
   ```


3. Wait for the complete API response and confirm that all requested channel data has been received before starting analysis. Do not analyze partial or incomplete data.

4. Wait until the collector confirms completion and all configured normalized files exist. If collection fails or a required file is missing, stop and report the error.

5. Run channel categorization first. Read the resolved run manifest at
   `<run-root>/manifest.json`, select the entry named
   `youtube-channel-categorization`, read its input file, and provide that
   input to the instruction file specified by the manifest. Wait for the
   subskill to finish, then read its output file. Verify only that the output
   file exists and contains content before continuing.

6. Run niche analysis in this order: 
read all data from `runs/<channel>/<run-id>/normalized/data-for-channel-niche-search-skill.json`; 
provide that data to the skill at `skills/find-channel-niches.md`; 
wait for the skill to finish; 
then save the skill's result to `runs/<channel>/<run-id>/skill-outputs/channel-niche-search-output.md`

7. Run the `channel-issues-orchestrator` entry from the resolved manifest. Give
   it the current run manifest and wait for it to run the configured issue
   subskills, save their individual outputs, and save the completed combined
   result to its configured output path.

   The quick workflow must not calculate, interpret, or replace subskill
   results. After the subskills finish, read the category and niche output
   files from the manifest and place their contents directly in the matching
   report fields.

8. Read the first non-empty lines from the completed
   `channel-issues-orchestrator-output.md` and place them directly in the
   `channel issues` field. Keep the individual specialist outputs available
   in the run folder for review.

## Testing output mode

During development and testing, display the completed result directly in the chat. Do not update Google Sheets, create spreadsheet rows, or perform external writes during this mode. Show the final quick-analysis fields in the required output format after the skill results have been validated.

When the application is explicitly switched to production output mode, the same validated result may be written to the matching Google Sheets row by normalized channel URL or channel ID.

## Required field mapping

The quick workflow must produce these fields in this order:

```text
channel name:
<channel name>

channel url:
<canonical channel URL>

channel category:
<Business, Healthcare, Education, or Creator>

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
- `channel category`: the exact one-label result from `youtube-channel-categorization`. Never infer this field from video topics or broad niche keywords.
- `current subscribers`: `statistics.subscriberCount`, formatted as a readable number.
- `niche`: the exact comma-separated result from `$find-channel-niches`.
- `country`: convert `snippet.country` to the full readable country name. Do not return the two-letter country code.
- `channel issues`: the saved performance and video SEO outputs.

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


