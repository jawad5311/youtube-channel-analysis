---
name: video-description-quality
description: Review video descriptions, record issues per video, and return the three to five issues shared by most videos.
---

# Video Description Quality

Read every provided video and inspect its description individually. Record all matching issues for each video internally before producing the final result.

Use the issue checks in this order.

1. After counting the common issues, if more than four distinct issues meet the half-of-videos threshold, add: descriptions looks unprofessional
2. If the video is longer than 8 minutes and has no recognizable chapters or timestamps, record: timestamps are missing
3. Compare the provided video tags with the description.
   - If no provided video tags or keywords appear naturally in the description, record: no keywords added in description
   - If only a small minority of the provided tags or keywords appear naturally in the description, record: very less keywords in description
   - Treat fewer than 20 percent of the provided tags or fewer than three relevant tags, when tags are available, as very less keywords
4. If the description has no clear call to action, record: no cta in the description
5. If the description has no relevant external, website, or social links, record: social or related links missing
6. Check hashtags.
   - No hashtags: hashtags missing
   - One or two hashtags: very less hashtags
   - Seven or more hashtags: too many hashtags
7. If the opening line is generic, weak, or not engaging, record: starts from a boring line

After reviewing every video, count each issue across all videos. Apply the descriptions looks unprofessional rule after the other issue counts are calculated. Treat an issue as common when it appears in at least half of the provided videos. Return the three to five highest-priority common issues, preserving the issue-check order supplied above when counts are tied. Return fewer than three issues only when fewer than three issues reach the half-of-videos threshold.

Return one lowercase line with the selected issues separated by comma and one space. Do not include counts, explanations, video titles, headings, recommendations, or per-video details. If no issue reaches the half-of-videos threshold, return exactly: no issues in video description