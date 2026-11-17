---
name: analyze-shorts-activity
description: Evaluate Shorts publishing frequency, recency, and schedule regularity from publication dates and upload gaps.
---

# Analyze Shorts Activity

Read `total_shorts`, `analysis_date`, `latest_short_published`, the formatted `publishedAt` values, and the ordered `shorts_gap` array. Use `first_short_published` only as a legacy alias when `latest_short_published` is absent. Evaluate the conditions from top to bottom and stop at the first matching condition. Recency always takes precedence over posting frequency and schedule regularity. The first Shorts record and first `shorts_gap` value represent the most recent Short. Return only the matching lowercase output line.

## Condition order

1. If no Shorts are provided, return:
   not creating shorts - missing a huge potential

2. If the most recent Short was published one or more years ago, return:
   published shorts x years ago - no current activity

   Replace x with the completed whole number of years.

3. If the most recent Short was published at least one completed month ago but less than one completed year ago, return:
   last short uploaded x month ago - no current activity

   Replace x with the completed whole number of months. Use months for the wording even when x is greater than one.

4. Evaluate all upload gaps, current-month activity, and weekly activity. Treat the schedule as irregular when the gaps show a break of more than 7 days, or repeated gaps of 5 or more days that make the weekly schedule inconsistent. Also treat a channel as irregular when it was active in the earlier observed history but has published only one or two Shorts during the current calendar month or the most recent 30-day period. In that case, return:
   irregular shorts posting - no content calendar

5. If the channel posts about one Short per week and the posting days are regular, return:
   posting 1 short a week - needs improvement

6. If the channel posts about one Short per week but the posting days are irregular, return:
   irregular shorts posting - only 1 per week

7. If the channel posts about two Shorts per week and the posting days are regular, return:
   posting 2 shorts a week - needs improvement

8. If the channel posts about two Shorts per week but the posting days are irregular, return:
   irregular shorts posting - only 2 per week

9. If the channel posts around three or more Shorts per week then return:
   no issues in short activity

## Frequency and regularity

Use all provided gaps and publication dates. Count Shorts per calendar week and inspect the variation between upload gaps. The first record is the latest Short and its gap is the rounded number of days since the analysis date. Each following gap is the rounded number of days since the previous Short.

A regular schedule has similar posting intervals and no repeated empty weeks. A weekly frequency with inconsistent days or long gaps is irregular. Do not use an average that hides an empty week or a long interruption.

Use the supplied gap values when available. Calculate from publication timestamps only when gap values are missing.

For recency, compare the latest publication date with the analysis date and count completed calendar months or years.

## Output

Return only one lowercase line. Do not include counts, explanations, headings, recommendations, or punctuation beyond the output text.


