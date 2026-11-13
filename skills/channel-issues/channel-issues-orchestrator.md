# Channel Issues Orchestrator

Use the current run manifest as the source of truth. Execute the configured
channel-issues entries in the order listed below. For each entry, read the
input file, provide it to the instruction file, wait for completion, and verify
that the output file exists and contains content.

## Testing execution mode

Run one subskill at a time in workflow order. Do not start the next subskill
until the current subskill has written a non-empty output file. Record the
completed output path before continuing.

## Workflow order

1. Performance analysis

   - Skill: skills/channel-issues/performance-analysis-skill.md
   - Input: <run-root>/normalized/channel-issues/data-for-performance-analysis-skill.json
   - Output: <run-root>/skill-outputs/channel-issues/performance-analysis-skill-output.md

2. Video SEO score

   - Skill: skills/channel-issues/video-seo-score.md
   - Input: <run-root>/normalized/channel-issues/data-for-video-seo-score-skill.json
   - Output: <run-root>/skill-outputs/channel-issues/video-seo-score-output.md

3. Video description quality

   Read the first non-empty line of the Video SEO Score output. Run this step
   only when that line is no issue in video seo.

   - Skill: skills/channel-issues/video-description-quality.md
   - Input: <run-root>/normalized/channel-issues/data-for-video-description-quality-skill.json
   - Output: <run-root>/skill-outputs/channel-issues/video-description-quality-output.md

4. Shorts activity

   - Skill: skills/channel-issues/analyze-shorts-activity.md
   - Input: <run-root>/normalized/channel-issues/data-for-shorts-activity-skill.json
   - Output: <run-root>/skill-outputs/channel-issues/analyze-shorts-activity-output.md

5. Thumbnail analysis

   - Skill: skills/channel-issues/thumbnail-analysis-skill.md
   - Input folder: <run-root>/normalized/channel-issues/thumbnail-analysis/
   - Output: <run-root>/skill-outputs/channel-issues/thumbnail-analysis-skill-output.md

6. Playlist analysis

   - Skill: skills/channel-issues/analyze-playlists.md
   - Input: <run-root>/normalized/channel-issues/data-for-playlist-analysis-skill.json
   - Output: <run-root>/skill-outputs/channel-issues/analyze-playlists-output.md

7. Community activity

   - Skill: skills/channel-issues/analyze-community-activity.md
   - Input: <run-root>/normalized/channel-issues/data-for-community-activity-skill.json
   - Output: <run-root>/skill-outputs/channel-issues/analyze-community-activity-output.md

8. Combined output

   Run this step only after every required or eligible subskill has a verified
   non-empty output file. Read the first non-empty line from the completed
   specialist output files in workflow order. Include a line only when it
   reports an actual issue that needs attention.

   Skip a subskill line when it reports any of the following:

   - no issue
   - no issues
   - no issues in
   - insufficient data
   - data is insufficient

   Treat case differences as equivalent when applying these skip rules. Keep
   issue lines exactly as written by the subskill, preserve their workflow
   order, and write only the retained issue lines to:

   <run-root>/skill-outputs/channel-issues/channel-issues-orchestrator-output.md

   If every subskill reports no issue or insufficient data, write exactly:

   `no channel issues found after analysis`

