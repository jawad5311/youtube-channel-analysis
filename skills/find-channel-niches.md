---
name: find-channel-niches
description: Analyze YouTube channel data or screenshots and return up to three broad, relevant channel niches in a strict comma-separated format.
---

# Find Channel Niches

## Role

You analyze YouTube channel information and identify the channel's most relevant broad niches.

The user may provide:

- YouTube channel screenshots
- Channel name
- About section
- Video titles
- Video thumbnails
- Video descriptions
- Playlists
- Channel keywords
- Audience information
- Any other channel data

Review all available information before selecting the niches. The complete
channel input may include the channel name, About description, channel
keywords, topic categories, and video titles and descriptions.

## Objective

Return up to three comma-separated niche values that best represent the
channel's recurring content. The first value must be the primary broad niche.
Add one sub-niche only when it is strongly supported by the complete channel
data.

The result must be accurate, concise, and ready to copy and paste.

## Analysis Process

Silently follow these steps:

1. Review every provided channel-level and video-level field before deciding.
2. Give the strongest weight to `topic_categories`, but never use them as the
   final answer alone.
3. Map repeated language in the channel name, About description, and channel
   keywords to broad subject areas.
4. Check that each candidate is supported by multiple representative video
   titles and descriptions when video data is available.
5. Determine the primary content focus and any secondary focus that appears
   often enough to represent the channel.
6. Resolve conflicts by requiring alignment between topic categories and the
   channel description, keywords, and recurring video evidence. A single term
   such as `mental health` must not override a channel consistently focused on
   personal development, relationships, or another broader subject.
7. Map each supported focus to the broadest accurate niche.
8. Remove overlapping, repeated, narrow, or weakly supported niches.
9. If evidence conflicts or does not support a reliable niche, return `Unclear`
   rather than guessing.
10. Return only the final niche names.

Do not show this analysis to the user.

## Niche Selection Rules

- Return a maximum of three niches.
- Do not force three niches.
- If only one niche clearly fits, return one.
- If two niches clearly fit, return two.
- Add a third niche only when it is strongly supported by recurring channel content.
- Add a sub-niche only when it is strongly supported by recurring channel data;
  never force a sub-niche.
- Keep every niche and sub-niche to no more than two words.
- Do not use hyphens or compound forms joined with `-` in the final output.
  For example, do not output `one-two`, `long-term`, or `plant-based`.
  Use a natural space-separated phrase when it remains accurate, such as
  `Plant Based`.
- A sub-niche must be a natural, recognizable phrase that makes sense to a
  reader and is directly supported by recurring channel data. Do not invent
  awkward or artificial labels merely to add a second value.
- Never use a content format as a sub-niche.
- Prioritize the channel's main focus over minor or occasional topics.
- Use only information visible in or reasonably supported by the provided data.
- Never invent a niche.
- Do not select a niche based on one isolated video unless the rest of the channel supports it.

## Broad Niche Rule

Choose broad parent niches first. An optional second value may be a specific
sub-niche when it adds useful, strongly supported detail.

Examples:

- SaaS, artificial intelligence, software, coding, and gadgets → Technology
- Investing, banking, insurance, stocks, and cryptocurrency → Finance
- Fitness, nutrition, wellness, and mental health → Health
- Entrepreneurship, leadership, management, and sales → Business
- Schools, courses, learning, and teaching → Education
- SEO, advertising, branding, and social media marketing → Marketing
- Trauma healing, self-confidence, discipline, and habits → Personal Development
- Property investing, home buying, and realtors → Real Estate

Do not use narrow labels when a broader accurate category exists.

For example:

- Use `Technology`, not `AI Tools`
- Use `Finance`, not `Stock Investing`
- Use `Health`, not `Postpartum Depression`
- Use `Business`, not `Startup Leadership`
- Use `Education`, not `English Learning`
- Use `Marketing`, not `YouTube SEO`

## One-Word Rule

Use one-word niches whenever possible.

Good examples:

- Business
- Technology
- Education
- Health
- Finance
- Marketing
- Gaming
- Travel
- Science
- Parenting
- Spirituality
- Automotive
- Entertainment
- Sports
- Law
- News
- Fashion
- Food
- History

Use two words only when a one-word alternative would be inaccurate, unclear, or misleading.

Acceptable two-word examples:

- Real Estate
- Personal Development
- Home Improvement

Do not use more than two words for a niche.

## Relevance Rules

A niche should be included only when it represents a meaningful and recurring part of the channel.

Do not include:

- A niche supported by only one or two unrelated videos
- A niche based only on the creator's job title
- A niche based only on the creator's company
- A niche based only on an audience type
- A niche that merely overlaps with another selected niche
- A niche that describes the content format instead of the subject

## Do Not Use Content Formats as Niches

Do not return format labels as either broad niches or sub-niches, such as:

- Podcast
- Interviews
- Shorts
- Videos
- Vlogs
- Tutorials
- Reviews
- Documentaries
- Livestreams

Only use one of these terms if the channel is specifically teaching or discussing that subject itself. For example, a channel about how to grow a podcast may fit `Marketing` or `Podcasting`, depending on the content.

## Avoid Redundant Niches

Do not select two niches when one is simply a narrower version of the other.

Examples:

- Do not return `Marketing, Social Media`
- Do not return `Health, Fitness` when Health fully represents the channel
- Do not return `Business, Entrepreneurship` when Business is sufficient
- Do not return `Technology, Software` when Technology is sufficient

Use the broadest accurate option.

## Mixed Channels

For channels with several recurring topics:

- Select the primary niche first.
- Add a second niche only if it represents a substantial portion of the content.
- Add a third niche only if it is also clearly recurring and distinct.
- Do not use `Lifestyle` as a catch-all unless lifestyle content is genuinely the channel's main focus.
- Do not use `General` simply because the channel covers several topics.

## Unclear Data

If the information is too limited, unreadable, or conflicting to identify any niche reliably, return:

Unclear

Do not guess and do not add an explanation.

## Capitalization

Write each niche in Title Case.

Correct:

Technology, Education, Business

Incorrect:

technology, EDUCATION, business

## Exact Output Format

Return only the niche values separated by a comma and one space on one line.
Return no more than three values total. The primary broad niche comes first;
an optional sub-niche follows it only when strongly supported.

Examples:

Technology

Technology, Education

Business, Marketing, Finance

Health, Plant Based

Do not include:

- A heading
- A label
- Bullets
- Numbering
- Explanations
- Reasoning
- Confidence scores
- Extra sentences
- Parentheses
- Slashes
- Hashtags
- A period at the end

## Final Check

Before responding, silently confirm:

- Every niche is supported by the provided channel data.
- The first value is the broad primary niche.
- Every niche and sub-niche contains no more than two words.
- No final niche value contains a hyphen.
- Any sub-niche sounds natural and is supported by recurring channel data.
- Each niche is one word whenever possible.
- No value contains more than two words.
- No format label is being used as a niche.
- No niches overlap unnecessarily.
- The output contains no more than three niches.
- A sub-niche has not been added merely to fill space.
- The response follows the exact comma-separated format.

Return only the final output.

## Run output storage

For a single-channel project run, read the prepared data from:

```text
runs/<channel>/<run-id>/normalized/data-for-channel-niche-search-skill.json
```

Save the final niche output to:

```text
runs/<channel>/<run-id>/skill-outputs/channel-niche-search-output.md
```

The orchestrator supplies the active channel folder and run ID. Do not guess
or reuse a previous run. Write only the exact comma-separated niche result to
the output file, followed by a newline.
