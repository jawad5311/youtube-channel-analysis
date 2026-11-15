---
name: analyze-playlists
description: Evaluate whether a YouTube channel creates and organizes public playlists and whether playlist titles and descriptions are SEO optimized.
---

# Analyze Playlists

Evaluate the supplied public playlist records and return one lowercase line. Return one or two comma-separated issue labels when applicable. Do not include headings, explanations, percentages, recommendations, or final punctuation.

## Evidence

Use the supplied custom public playlists. Each playlist record should contain its title, description, playlist URL or ID, item count, and included video titles when available.

Ignore YouTube system playlists such as Uploads, Likes, and Favorites. Do not treat a channel's video count as evidence that it creates playlists. If playlist collection is incomplete or the records do not identify public custom playlists, return `insufficient data to evaluate playlists` unless verified page evidence establishes that no public playlists exist.

## Checks

1. Determine whether the channel creates public custom playlists.
2. Check whether the playlists contain relevant videos and organize content into clear topic, series, format, or audience groups.
3. For every playlist, inspect the title and description. Give the greatest weight to the description. A playlist is SEO optimized only when its description is detailed, clearly explains the included content, relates to the playlist title and videos, and naturally includes relevant channel keywords or tags.
4. Treat missing, empty, or very short descriptions as not SEO optimized even when the playlist title contains keywords. Treat descriptions without relevant channel keywords, channel tags, or topic keywords as not SEO optimized.
5. Add the `itemCount` values across all supplied public custom playlists and compare that sum with `total_public_videos`. If the playlist sum is lower than total public videos, report that content is not fully organized in playlists. If the sum is equal to or greater than total public videos, do not report an organization issue. Do not report this comparison when either total is missing.

## Final verdict rules

Apply these checks in order and retain every issue that applies:

- zero public custom playlists -> `creating no playlists`
- the sum of playlist `itemCount` values is lower than `total_public_videos` -> `not organizing content in playlists`
- one or more playlists lack a detailed, keyword-relevant description -> `playlists are not seo optimized`
- public playlists exist, their item-count coverage reaches total public videos, and every playlist has a detailed keyword-relevant description -> `no issues in playlists`

When both organization and SEO issues apply, return exactly:

`not organizing content in playlists, playlists are not seo optimized`

When only one issue applies, return that single label. A larger playlist item sum can result from videos appearing in multiple playlists and does not prove unique coverage, but it does not trigger the organization issue under this rule.

## Output

Return only one of these exact lines:

```text
creating no playlists
```

```text
not organizing content in playlists
```

```text
playlists are not seo optimized
```

```text
not organizing content in playlists, playlists are not seo optimized
```

```text
no issues in playlists
```

