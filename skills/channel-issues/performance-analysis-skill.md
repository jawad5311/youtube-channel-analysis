# Performance Analysis Skill

Analyze the recent long-form video performance using the prepared performance
input file at:

`normalized/channel-issues/data-for-performance-analysis-skill.json`

The input contains up to 30 videos ordered newest first, the
configured outliers removed, per-video reach percentages, subscriber count,
average views, total views, and average view percentage.

Use the prepared `average_view_percentage` and `average_views` values to select
the performance issue. Return only one line when an issue applies:

1. If average reach is below 10% **or** average views are below 1,000, return:

   `Videos are not getting views - very low reach`

2. If average reach is from 10% through 20%, return:

   `Limited video views - moderate reach - can be improved`



The first rule has priority when both conditions are present. Do not return
multiple performance lines, explanations, recommendations, or positive
performance statements. The channel issues orchestrator will combine this
single line with findings from the other specialist skills.


