---
name: analyze-playlists
description: Evaluate whether a YouTube channel creates and organizes public playlists and whether playlist titles and descriptions are SEO optimized.
---

# Analyze Playlists

Evaluate the supplied public playlist records and return exactly one lowercase line. Do not include headings, explanations, percentages, recommendations, or final punctuation.

## Evidence

Use the supplied custom public playlists. Each playlist record should contain its title, description, playlist URL or ID, item count, and included video titles when available.

Ignore YouTube system playlists such as Uploads, Likes, and Favorites. Do not treat a channel's video count as evidence that it creates playlists. If playlist collection is incomplete or the records do not identify public custom playlists, return `insufficient data to evaluate playlists` unless verified page evidence establishes that no public playlists exist.

## Checks

1. Determine whether the channel creates public custom playlists.
2. Check whether the playlists contain relevant videos and organize content into clear topic, series, format, or audience groups.
3. For every playlist, inspect the title and description. Check whether the title clearly describes the content, the description is detailed enough to explain the playlist, and relevant channel or topic keywords are used naturally.
4. Treat missing, empty, or very short playlist descriptions as not SEO optimized. Treat descriptions with no meaningful relationship to the playlist title and included video topics as not SEO optimized.

## Final verdict rules

Apply these rules in order:

- Verified zero public custom playlists -> `creating no playlists`
- Public playlists exist but content is missing, scattered, duplicated, or not organized into meaningful groups -> `playlists are not organized`
- Playlists exist and content is organized, but one or more meaningful playlists have weak, missing, or non-keyword-focused descriptions -> `playlists are not seo optimized`
- Playlists exist, contain relevant organized content, and their titles and descriptions are detailed and keyword relevant -> `playlists are seo optimized`

If both organization and SEO have problems, return `playlists are not organized` because organization is the more basic issue. Do not call a playlist SEO optimized because it has a keyword in its title alone.

## Output

Return only one of these exact lines:

```text
creating no playlists
```

```text
playlists are not organized
```

```text
playlists are not seo optimized
```

```text
playlists are seo optimized
```

```text
insufficient data to evaluate playlists
```
