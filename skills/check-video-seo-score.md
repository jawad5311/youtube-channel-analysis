---
name: check-video-seo-score
description: Evaluate the SEO setup and description quality of a set of YouTube videos, then return one concise final video-SEO verdict.
---

# Check Video SEO Score

Evaluate each provided YouTube video individually, then combine the results into one final verdict. The final response must be one lowercase line only. Do not include headings, explanations, video names, scores, percentages, bullets, or recommendations.

## Required evidence

Use the provided video records. Each record should contain, when available:

- Video title and URL
- `snippet.description`
- `snippet.tags`
- `contentDetails.duration`
- Publication date

If the records do not contain enough information to evaluate the videos, return:

```text
insufficient data to evaluate video seo
```

## Per-video checks

Evaluate every video silently using these checks:

1. Confirm whether `snippet.tags` contains meaningful keywords/tags. An empty or missing tags array means the video has no video SEO tags.
2. Compare the tags with the video title and description. Check whether important tags are naturally represented in the description and whether the tags match the actual video topic.
3. Check whether the description is professionally written. Look for a clear opening line, a useful explanation of the video, readable structure, and enough context for the viewer.
4. For videos longer than 10 minutes, check whether timestamp chapters are included in the description. Treat a timestamp list as present only when it contains recognizable time markers such as `00:00`, `01:25`, or `1:25`.
5. Check whether the description includes a relevant call to action.
6. Check whether the description includes social or external links where appropriate.
7. Check whether the description includes relevant hashtags.

A video is fully SEO optimized only when its tags/keywords are present and relevant, the tags are reasonably reflected in the description, the description is professionally written and explains the video clearly, required chapters are present for videos longer than 10 minutes, and the description includes an appropriate CTA, relevant links, and hashtags.

## Per-video outcome rules

Use these internal outcome patterns:

- No tags/keywords and a poor description → `no video seo, no proper video description`
- Tags/keywords are present but the description is unprofessional or incomplete → `no proper description, seo needs improvements`
- No tags/keywords but the description is reasonably good while some description elements are missing → `no video seo, description needs improvement`
- All required SEO and description checks are good → `videos are seo optimized`

Do not expose the per-video outcomes in the final response.

## Combined verdict rules

Let `fully_optimized_percentage` be the percentage of evaluated videos that are fully SEO optimized.

- If at least 70% of videos are fully optimized, return exactly:

```text
videos are seo optimized
```

- If fewer than 60% are fully optimized, base the final line on the most common problems among the remaining videos. Use one of the exact outcomes above. If the remaining problems are mixed, use the outcome that reflects the broader weakness; missing tags takes precedence when tags are absent across the majority, while poor descriptions takes precedence when tags are present but descriptions are consistently weak.
- If 60% through 69% are fully optimized, return:

```text
seo needs improvements
```

Use the exact lowercase wording. Do not add a period or any other text.

## Final output

Return only one of these result patterns:

```text
no video seo, no proper video description
```

```text
no proper description, seo needs improvements
```

```text
no video seo, description needs improvement
```

```text
videos are seo optimized
```

```text
seo needs improvements
```

```text
insufficient data to evaluate video seo
```