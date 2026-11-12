---
name: thumbnail-analysis-skill
description: Compare channel thumbnails with the banner and with one another to identify shared branding, consistency, readability, topic alignment, and changes over time.
---

# Thumbnail Analysis Skill

Read every image in the supplied input folder. The folder contains `banner.png` and thumbnail files named `video-1.png`, `video-2.png`, and so on. The first thumbnail is the most recent video and higher numbers are older videos. Analyze each available thumbnail individually before identifying the issues shared by the thumbnails.

Use `banner.png` as the channel branding reference. Compare the thumbnails with the banner for visual matching, including the main and accent colors, typography, logos or symbols, graphic treatments, shapes, patterns, imagery, and overall visual mood.

Compare the thumbnails with one another for repeated typography, consistent graphics, a stable layout or composition pattern, recognizable logos or symbols, consistent visual hierarchy, and a coherent color palette. Check whether the thumbnails feel like one channel while still distinguishing individual videos.

Evaluate readability in every thumbnail. Check text size, text contrast, number of words, subject visibility, separation between the subject and background, clutter, and readability at mobile thumbnail size.

Check whether the visual treatment represents the channel's actual topic and positioning. Health content should use imagery and language appropriate to health. Business content should look professional and trustworthy. Educational content should make the subject clear. Creator-led content should consistently represent the creator.

Compare recent thumbnails with older thumbnails in file order. Identify whether branding has become more consistent, whether the channel changed its visual identity, whether the banner matches the current or older thumbnail style, and whether multiple unrelated design eras exist.

Only report issues that appear repeatedly across the thumbnails. Ignore an issue that occurs in just one thumbnail unless it indicates a clear channel-wide style problem. Use concise lowercase issue descriptions of no more than three words, such as `weak branding`, `inconsistent style`, `inconsistent graphics`, `unstable layout`, `small text`, `low contrast`, `text overload`, `poor visibility`, `weak separation`, `banner mismatch`, `topic mismatch`, or `mixed design eras`.

If one or more repeated issues are found, return exactly one lowercase line in this format:

`thumbnails look unprofessional, issue 1, issue 2, issue 3`

Start the line with exactly `thumbnails look unprofessional`. After that phrase, include only two or three common issues found in the images, in order of impact. Every issue must be no more than three words long. Do not add headings, explanations, counts, recommendations, or punctuation other than the commas separating issues.

If no repeated thumbnail issues are found, return exactly:

`no issues in thumbnails`
