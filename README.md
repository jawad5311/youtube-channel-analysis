# YouTube Channel Analysis

A modular YouTube channel analysis project with shared collectors, focused analysis skills, and quick-analysis workflows.

## Project areas

- `src/collectors/` collects channel metadata and recent video data.
- `src/analysis/` contains analysis logic for quick channel results.
- `src/workflows/` runs end-to-end analysis workflows.
- `skills/` contains the quick-analysis and specialist skill instructions.
- `tests/` contains offline tests using fake API clients.
- `runs/` stores local generated results and is ignored by Git.

## Setup

1. Create a virtual environment.
2. Install the dependencies from `requirements.txt`.
3. Copy `.env.example` to `.env`.
4. Set `YOUTUBE_API_KEY` in `.env`, or set `YOUTUBE_API_KEY_FILE` to a separate
   text file containing only the key. Relative key-file paths are resolved from
   the `.env` file's folder.

You can also paste the path directly into the root-level `api-key-path.txt`
file. Put one path on one line. The workflow reads this file automatically
when no API key is already set.

Country output uses common CRM-friendly names for GoHighLevel, including
`United States`, `UK`, `South Korea`, and `Russia`.

The `.env` file and generated run data are excluded from Git.

## Run quick analysis

```powershell
python -m src.workflows.quick_channel_analysis https://youtube.com/@channelhandle
```

## Collection and skill inputs

`config/quick-channel-collection.json` controls API collection fields and counts.
`config/quick-analysis-inputs.json` selects which collected fields are written for
each configured skill. Empty skill sections are skipped. False fields are omitted;
missing requested values are reported in `missing_data` rather than fetched again.

```powershell
python -m src.workflows.quick_channel_analysis https://youtube.com/@channelhandle --collection-config config/quick-channel-collection.json --inputs-config config/quick-analysis-inputs.json
```

Collected data is saved in `normalized/collection.json`. Skill packages are saved as
`normalized/data-for-channel-categorization.json`, `data-for-channel-niche-search.json`,
and `data-for-channel-issues.json`, relative to that same normalized directory.
Skill record selectors use a one-item list such as `"videos": [{"title": true}]`,
with optional `total_videos`, `total_shorts`, `total_playlists`, and
`total_community_posts` limits. Channel selectors include `channel_name`,
`channel_description`, `channel_tags`, `country`, and `subscriber_count`.

The API collector cannot confirm Shorts from duration alone. It saves uploads over
180 seconds as videos and shorter uploads as unconfirmed Shorts candidates. Duration
is requested internally for classification even when omitted from output fields.
IDs are used internally for API requests but excluded from skill packages.

Community posts are not collected by the API worker. When enabled, a
`browser-collection-request.json` handoff is saved with the configured limit and
coverage requirements. The community status stays `pending_browser` until browser
collection is performed. Activity coverage settings do not override item limits or
claim that sufficient history has been obtained. Thumbnail and banner fields save
image URLs; they do not download image files or perform visual analysis.

## Run tests

```powershell
python -m unittest discover -s tests -p "test_*.py"
```

The tests use fake clients and do not make YouTube API requests.

## Connect Google Sheets

Create an OAuth client of type Desktop app in Google Cloud Console and save the downloaded JSON credentials as config/google-oauth-client.json. Install the dependencies, then start the local authorization flow with:

    python -m src.integrations.google_sheets_auth

The browser authorization flow saves a refreshable token to
`config/google-sheets-token.json`. Both files are ignored by Git.

### Refresh Google Sheet columns

Copy `config/google-sheet-url.example.txt` to `config/google-sheet-url.txt`
and paste your Google Sheet URL into the new file. Your URL file is local and
is not committed to Git.

The Sheets updater refreshes `config/google-sheet-columns.txt` on the first
update run after the 24-hour cooldown expires. It uses row 1 from its existing
sheet read, so the refresh adds no API request. Column positions for writes
come from that same live header row.

To run the column reader independently, use:

```powershell
python -m src.integrations.google_sheet_columns
```

The command uses `config/google-sheet-url.txt` and the cached tab name. Pass
`--sheet-name "Sheet1"` to select a tab or initialize a cache for a new
spreadsheet. Add `--force` to fetch row 1 immediately. A successful fetch
restarts the cooldown, even if the headers are identical.
