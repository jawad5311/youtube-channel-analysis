# Channel Issues Orchestrator

Use this parent skill to produce the `channel issues` field for the quick channel analysis. It coordinates the specialist checks, validates their evidence, and returns three to five concise issue lines.

## Specialist checks

Run each check only when its required evidence is available:

- `check-video-seo-score` for recent video titles, descriptions, and SEO setup.
- `video-seo-analysis-skill` for broader video SEO findings.
- `thumbnail-analysis-skill` for thumbnail evidence.
- `performance-analysis-skill` for views and performance evidence.
- `content-strategy-analysis-skill` for recurring content patterns.
- `analyze-playlists` for public playlist organization and SEO.
- `analyze-shorts-activity` for Shorts publishing consistency.
- `analyze-community-activity` for the channel Posts page.

## Workflow order

Use `config/quick-analysis-inputs.json` as the source of truth for the enabled
channel-issues skills, their manifest-defined input paths, and their data fields.
Run the configured skills in the same object order shown in that file. For
every step, read the skill's configured input from the current run, provide
that data to the matching skill, wait for the skill to finish, and save its
result to the matching file in `runs/<channel>/<run-id>/skill-outputs/channel-issues/`.

1. **Performance analysis**

   Read `runs/<channel>/<run-id>/normalized/channel-issues/data-for-performance-analysis-skill.json`, provide it to `skills/channel-issues/performance-analysis-skill.md`, and save the result to `runs/<channel>/<run-id>/skill-outputs/channel-issues/performance-analysis-skill-output.md`.

2. **Video SEO score**

   Read `runs/<channel>/<run-id>/normalized/channel-issues/data-for-video-seo-score-skill.json`, provide it to `skills/channel-issues/check-video-seo-score.md`, and save the result to `runs/<channel>/<run-id>/skill-outputs/channel-issues/check-video-seo-score-output.md`.

3. **Shorts activity**

   Read `runs/<channel>/<run-id>/normalized/channel-issues/data-for-shorts-activity-skill.json`, provide it to `skills/channel-issues/analyze-shorts-activity.md`, and save the result to `runs/<channel>/<run-id>/skill-outputs/channel-issues/analyze-shorts-activity-output.md`.

4. **Thumbnail analysis**

   Read `runs/<channel>/<run-id>/normalized/channel-issues/data-for-thumbnail-analysis-skill.json`, provide it to `skills/channel-issues/thumbnail-analysis-skill.md`, and save the result to `runs/<channel>/<run-id>/skill-outputs/channel-issues/thumbnail-analysis-skill-output.md`.

5. **Playlist analysis**

   Read `runs/<channel>/<run-id>/normalized/channel-issues/data-for-playlist-analysis-skill.json`, provide it to `skills/channel-issues/analyze-playlists.md`, and save the result to `runs/<channel>/<run-id>/skill-outputs/channel-issues/analyze-playlists-output.md`.

6. **Community activity**

   Read `runs/<channel>/<run-id>/normalized/channel-issues/data-for-community-activity-skill.json`, provide it to `skills/channel-issues/analyze-community-activity.md`, and save the result to `runs/<channel>/<run-id>/skill-outputs/channel-issues/analyze-community-activity-output.md`.

7. **Content strategy analysis**

   Read `runs/<channel>/<run-id>/normalized/channel-issues/data-for-content-strategy-analysis-skill.json`, provide it to `skills/channel-issues/content-strategy-analysis-skill.md`, and save the result to `runs/<channel>/<run-id>/skill-outputs/channel-issues/content-strategy-analysis-skill-output.md`.

8. **Video SEO analysis**

   Read `runs/<channel>/<run-id>/normalized/channel-issues/data-for-video-seo-analysis-skill.json`, provide it to `skills/channel-issues/video-seo-analysis-skill.md`, and save the result to `runs/<channel>/<run-id>/skill-outputs/channel-issues/video-seo-analysis-skill-output.md`.

9. **Channel issues orchestrator output**

   Use the completed specialist outputs to prepare the orchestrator result at `runs/<channel>/<run-id>/skill-outputs/channel-issues/channel-issues-orchestrator-output.md`. Keep synthesis disabled until explicitly enabled by the workflow configuration.

## Specialist result contract

Each completed specialist returns structured findings with an area, issue, evidence, severity, and confidence. A failed or unavailable check returns insufficient data for that area and must not create an issue.

## Synthesis rules

1. Keep only supported, actionable findings.
2. Merge duplicate findings across specialists.
3. Prioritize the highest-impact findings, then the strongest evidence.
4. Return three to five lines when enough findings exist.
5. Return fewer lines when fewer supported findings exist.
6. Return `No channel issues were found.` when no supported issue exists.

Return one concise issue per line, without area labels, severity labels, evidence details, or recommendations. Do not invent findings when a specialist lacks evidence.
