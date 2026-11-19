---
name: performance-analysis-skill
description: Evaluate recent long-form video views against subscribers using per-video reach and a 70 percent threshold.
---

# Performance Analysis Skill

Analyze the selected recent long-form videos in `normalized/channel-issues/data-for-performance-analysis-skill.json`. The input already applies the configured age, sample-size, and outlier filters. Do not remove additional videos.

For each video with a valid nonnegative `viewCount`, calculate its views as a percentage of `subscriber_count` when the subscriber count is positive. Use the same subscriber count for every video. Do not substitute average views or average reach for individual results.

Classify each video in order:

1. **Very low reach:** fewer than 1,000 views, or views below 5% of subscribers.
2. **Moderate reach:** at least 1,000 views and views from 5% through 15% of subscribers.
3. **Other:** at least 1,000 views and views above 15% of subscribers.

Count the share of analyzed videos in each category. If at least 70% are very low reach, return exactly:

`Videos are not getting views - very low reach`

Otherwise, if at least 70% are moderate reach, return exactly:

`Limited video views - moderate reach - can be improved`

Otherwise calculate average views across all selected videos after the configured filters and calculate average views as a percentage of subscribers. If average views are below 1,000 or the average ratio is below 5%, return exactly `Videos are not getting views - very low reach`. Otherwise, if the average ratio is from 5% through 15%, return exactly `Limited video views - moderate reach - can be improved`. Otherwise return exactly:

`no issue in video performance`

If there are no selected videos, any selected video lacks a valid view count, or subscriber count is missing, hidden, or not positive, return exactly `insufficient data to evaluate video performance`. Do not treat missing data as zero or reduce the denominator. Return one line only. The channel issues orchestrator omits no-issue and insufficient-data results from the combined issues.
