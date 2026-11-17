---
name: quick-channel-analysis
description: Run the YouTube channel analysis workflow for one supplied channel reference.
---

# Quick Channel Analysis

Run the workflow in this order:

1. Pass the supplied channel reference to `orchestrator.py`.
2. Wait for the Python workflow to complete successfully.
3. Wait for fetching to complete successfully. Confirm that the run manifest,
   normalized inputs, banner, thumbnails, and every other required asset exist.
   Treat the successful completion of `orchestrator.py` as the end of the
   preparation phase and as the handoff point for the skill-execution phase.
   Do not return a result at this checkpoint.
4. Run channel categorization using:
   - Input: `<run-root>/normalized/data-for-channel-categorization-skill.json`
   - Skill: `skills/youtube-channel-categorization.md`
   - Output: `<run-root>/skill-outputs/channel-categorization-output.md`
5. Run channel niche analysis using:
   - Input: `<run-root>/normalized/data-for-channel-niche-search-skill.json`
   - Skill: `skills/find-channel-niches.md`
   - Output: `<run-root>/skill-outputs/channel-niche-search-output.md`
6. Run the channel-issues orchestrator using:
   - Skill: `skills/channel-issues/channel-issues-orchestrator.md`
   The channel-issues orchestrator manages the input paths, skill instruction
   paths, and output paths for all channel-issues sub-skills.
7. Wait for every configured skill to complete and write its output.
8. Read the completed category, niche, and channel-issues outputs.
9. Export the completed analysis to the configured Google Sheet before returning
   the final result. From the project root, run the following with the working
   Python interpreter, substituting the exact run root returned in step 3 and
   the canonical channel URL. Use the spreadsheet configured in
   `config/google-sheet-url.txt`.

   ```powershell
   python -m src.integrations.google_sheet_update --run-dir "<run-root>" --channel-url "<canonical-channel-url>"
   ```

   Wait for the command and report how many matching rows it updated. A result
   of zero means the channel has no matching row. If export fails, report the
   error and include the completed local analysis. Verify the command's exit
   code and `<run-root>/sheet-export-status.json`: `updated` with a positive
   row count confirms export, `no_matching_rows` means nothing was updated,
   and `failed` or a missing receipt means export is not confirmed. If network
   access is blocked, retry with the available network permission mechanism.
   Never describe collection or specialist analysis alone as a completed sheet
   update. Do not stop or ask to continue at the collection or analysis handoff.
10. Return the final quick channel analysis and the Google Sheets update status.

Do not continue to the next step when the previous step fails or has missing required output.
After step 3, begin a separate skill-execution phase using the returned
`<run-root>`. The assistant must perform steps 4–10 after the Python command
returns. Do not treat `Status: ready for Codex skills` as the final result and
do not report completion while the skill outputs are empty.

Return the final result in this order:

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
<niche result>

country:
<full country name, except use UK for the United Kingdom>

channel issues:
<channel issues result>
```

Do not replace completed skill outputs with Python fallbacks.

## Skill execution status

During steps 4–7, report each configured skill immediately after execution with one status line:

`skill status: <skill name> - executed successfully`

or, when execution fails or required input or output is missing:

`skill status: <skill name> - not executed successfully - <reason>`

The status line must appear on screen. Do not write execution status into a specialist skill output file. Specialist output files must contain only that skill's analysis result. Do not mark a skill successful until its output file exists and is non-empty. For thumbnail analysis, inspect every image file in the supplied thumbnail input folder, including the banner when present. For community activity, use the completed HTTP `/posts` collection when available, and use the browser handoff only when HTTP collection fails. The final result may be returned only after all required skills have a status line.


