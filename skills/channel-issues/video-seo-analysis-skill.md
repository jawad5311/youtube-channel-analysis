# Video SEO Analysis Skill

Analyze the SEO of the channel's collected videos. The skill must receive the
following three fields for every video being reviewed:

- `title`
- `description`
- `tags` (the keywords/tags added to the video)

Review each field across the available videos and identify recurring problems:

- Titles that are unclear, too short, repetitive, or missing the main search topic.
- Descriptions that are missing, too short, duplicated, poorly structured, or do not explain the video's search intent.
- Tags that are missing, too sparse, unrelated, repetitive, or fail to support the video's topic.

Use the video title, description, and tags together. Do not infer missing tags
from the title, and do not claim a field is optimized when that field was not
collected. Report patterns across multiple videos instead of treating one
unusual upload as a channel-wide issue.

Return structured findings in this format:

```json
{
  "area": "video_seo",
  "issue": "Video descriptions are frequently too short to support search intent.",
  "evidence": "12 of 20 reviewed videos have descriptions under 150 characters.",
  "severity": "medium",
  "confidence": "high"
}
```

Return only supported findings. The channel issues orchestrator will merge
duplicates and convert the strongest findings into concise output lines.
