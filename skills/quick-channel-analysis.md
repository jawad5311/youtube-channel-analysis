---
name: quick-channel-analysis
description: Run the YouTube channel analysis workflow for one supplied channel reference.
---

# Quick Channel Analysis

Run the workflow in this order:

1. Pass the supplied channel reference to `orchestrator.py`.
2. Wait for the Python workflow to complete successfully.
3. Wait for fetching to complete successfully. Confirm that the run manifest,
   normalized inputs, banner, thumbnails, and every other required asset exist.
   Treat the successful completion of `orchestrator.py` as the end of the
   preparation phase and as the handoff point for the skill-execution phase.
   Do not return a result at this checkpoint.
4. Run channel categorization using:
   - Input: `<run-root>/normalized/data-for-channel-categorization-skill.json`
   - Skill: `skills/youtube-channel-categorization.md`
   - Output: `<run-root>/skill-outputs/channel-categorization-output.md`
5. Run channel niche analysis using:
   - Input: `<run-root>/normalized/data-for-channel-niche-search-skill.json`
   - Skill: `skills/find-channel-niches.md`
   - Output: `<run-root>/skill-outputs/channel-niche-search-output.md`
6. Run the channel-issues orchestrator using:
   - Skill: `skills/channel-issues/channel-issues-orchestrator.md`
   The channel-issues orchestrator manages the input paths, skill instruction
   paths, and output paths for all channel-issues sub-skills.
7. Wait for every configured skill to complete and write its output.
8. Read the completed category, niche, and channel-issues outputs.
9. Return the final quick channel analysis.

Do not continue to the next step when the previous step fails or has missing required output.
After step 3, begin a separate skill-execution phase using the returned
`<run-root>`. The assistant must perform steps 4–9 after the Python command
returns. Do not treat `Status: ready for Codex skills` as the final result and
do not report completion while the skill outputs are empty.

Return the final result in this order:

```text
channel name:
<channel name>

channel url:
<canonical channel URL>

channel category:
<Business, Healthcare, Education, or Creator>

current subscribers:
<subscriber count>

niche:
<niche result>

country:
<full country name>

channel issues:
<channel issues result>
```

Do not replace completed skill outputs with Python fallbacks.
