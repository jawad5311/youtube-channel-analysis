---
name: video-seo-score
description: Score video titles, descriptions, and tags, then return a verdict with a summary and per-video scoring details.
---

# Video SEO Score

Read the provided video data and evaluate every video individually. Calculate the verdict from the scores first. Then write the summary and per-video scoring details from that completed evaluation. The summary and details must not change the verdict.

## Tag score out of 50

- 400 or more tag characters: 50
- 200 to 399 tag characters: 30
- 100 to 199 tag characters: 20
- Missing tags or fewer than 100 characters: 0

## Description score out of 40

Use these weights.

- Clear opening or catchy first line: 5
- Specific context about what viewers will learn, see, or accomplish: 7
- Readable structure with short paragraphs, headings, or bullets: 5
- Chapters or timestamps when useful: 5
- Video tags or target keywords naturally used in the description: 5
- Relevant call to action: 5
- Relevant links or social links: 3
- Three to five relevant hashtags: 5

If more than five hashtags are present, award 0 for the hashtag criterion. Do not award points for missing features or infer missing data.

## Title score out of 10

Score clarity, clickability, and alignment with the description and tags.

## Final verdict

If at least 80% of the videos score above 60, return exactly `no issue in video seo`. This rule takes priority over the other verdict conditions.

- If no videos are SEO optimized, or most score below 20, return videos are not seo optimized
- If most score from 30 through 50 and some score below 30, return videos not properly seo optimized
- If some score above 60 and some score from 20 through 50, return some videos are not properly seo optimized
- If some score above 60 and some score below 20, return some videos are not seo optimized

A score above 60 counts as SEO optimized. The `no issue in video seo` result means that at least 80% of the evaluated videos are SEO optimized. A score below 20 counts as not SEO optimized. Use the most specific matching condition when more than one applies.

## Output format

Write the result in this order.

1. First line. Return exactly one lowercase verdict line.
2. After a blank line. Give a short plain-language summary explaining the main reasons for the verdict.
3. After another blank line. Give one scoring block for every provided video, in the original input order. Each block must include:
   - Video title
   - Tags score out of 50
   - Description score out of 40
   - Title score out of 10
   - Total score out of 100
   - One short reason for the scores

The total score for each video must equal the sum of its tag, description, and title scores. Include a block even when a video has missing tags or other missing fields. State the missing evidence in that video''s reason.

The first line is the machine-readable verdict used by the quick channel analysis workflow. The summary and scoring blocks are for manual review and must not alter the first-line verdict.

Do not add recommendations. Do not include a second verdict.

The allowed first-line verdict `no issue in video seo` must be used when its 80% threshold is met.

