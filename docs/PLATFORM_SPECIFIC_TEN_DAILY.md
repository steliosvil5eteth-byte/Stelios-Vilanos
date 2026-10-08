# PLATFORM_SPECIFIC_TEN_DAILY

## Current result

The user's instruction of 8 October 2026, reconfirmed at 08:53 Europe/Athens, replaces shared publishing with **40 distinct narrated videos per day: 10 each for Facebook, Instagram, TikTok and YouTube**. Each story belongs to one platform only. Brand: 7076410, «Ιστορίες που μας αγγίζουν».

`config/platform_growth_strategy.json` is the sole current policy. It is **disabled** with state `BLOCKED_REQUIRED_HISTORY_AND_ZERO_CREDIT_CAPACITY`. This is a prepared editorial and operational policy, not a running forty-video production service. No new video was rendered or scheduled during this transition.

## What changed

- Nine remaining legacy shared Metricool records were changed to inactive drafts, covering 27 Facebook/Instagram/TikTok destinations. Their media and text were retained.
- The previous YouTube withdrawal remains in force. Published posts were preserved. The verified transition snapshot contained five published items per platform and zero active pending items per platform.
- Two governing Notion pages and nineteen legacy unpublished source records were updated. The nineteen are Blocked with no target platform. Ten of these were source packs for 9 October, not live scheduled Metricool posts.
- Legacy common and YouTube-only configuration files are superseded. They cannot supply current production authorization.
- Thirty-five identified Azure workflow entrypoints are held at the current head. The 9 October renderer additionally checks the new policy before importing production dependencies. Its manifest and guard must be committed atomically: changing the manifest alone would otherwise trigger the old renderer.
- Existing production and reporting automations receive the new policy guard. The daily production and midday recovery tasks remain disabled; enabled monitoring/prebuild tasks may research or report while blocked, but may not generate, recreate a queue, or publish.

The private delivery journal retains record IDs, preimages, readbacks, current drafts, and complete account evidence. Private account analytics and raw Notion or automation payloads are not part of this public repository.

## Editorial allocation

These are initial test allocations, not proven optimal ratios. A topic that previously performed well is evidence for research, not permission to reuse its existing story.

| Platform | Initial allocation of ten original videos |
|---|---|
| Facebook | 4 human relationship/decision stories, 3 documented human histories, 2 zodiac stories explicitly framed as entertainment, 1 labeled folklore story |
| Instagram | 4 place histories, 3 natural phenomena, 2 art/object histories, 1 human story tied to a place |
| TikTok | 4 fictional human mysteries with complete resolution, 3 documented curiosities, 2 labeled folklore stories, 1 science question |
| YouTube | 4 clear science/history questions, 3 human decisions, 2 Greek microhistories, 1 labeled myth |

Historical TikTok photo results must be assessed separately from videos. Facebook reach must not be compared directly with Reel views. Instagram shares must not be called DM sends without corresponding data. Missing or ambiguously scaled metrics must remain unknown.

Compare new original videos after equivalent 24-hour, 72-hour and seven-day observation windows, controlling for platform, format and duration band. Use valid watch duration, retention, saves/shares and attributable follows; treat views as one signal. One outlier cannot establish typical performance.

The user chooses ten per day. YouTube explicitly states that there is no minimum posting cadence required for performance: [official Shorts discovery guidance](https://support.google.com/youtube/answer/11914225?co=YOUTUBE._YTVideoType%3Dshorts&hl=en).

## Required creative form

- Complete original Greek narration in **Νέστορας / el-GR-NestorasNeural**, at least 80 seconds, target 80–110 seconds when the story supports it. YouTube hard maximum remains 150 seconds.
- A concrete first-scene question, conflict or decision, with a complete ending in the same video.
- Photographic or photorealistic relevant and distinct scenes, verified rights, no children's faces, no avatar, no second/background music.
- Burned-in Greek subtitles synchronized to the final audio, readable on mobile.
- Exact CTA: «Αν σας άρεσε, ακολουθήστε για περισσότερα.» Up to five hashtags.
- Verify factual claims against suitable sources; mark invented stories and folklore honestly. Do not copy plots, scripts, footage or creator watermarks.
- Check the platform's actual native AI disclosure field and any applicable monetization limitations. A caption alone is not assumed to replace the required control.
- No filler, silence padding or scene duplication to reach a duration. A slide show with pan/zoom is not proof of monetization eligibility.

## Hard blockers

### Authorized fresh history

A required Notion archive query returned `usage_limit_reached` / entitlement. Do not automatically retry that denied query, use another route to evade the restriction, or describe cached data as a successful fresh check. Known-page administrative updates do not establish duplicate clearance.

Before any new script/media or scheduling action, the authorized workflow must successfully reconcile live Metricool, fresh Notion history, repository history and the production lease/delivery ledger. If one required source is unavailable, content creation and release remain blocked.

### Exact voice with zero credits

The actual Azure SKU and remaining allowance have not been verified. A filename or provider label containing F0 is not proof of an F0 account or available free capacity.

The published Azure F0 limits are 500,000 neural TTS characters and five hours of real-time speech recognition per month: [official pricing](https://azure.microsoft.com/en-us/pricing/details/speech/).

An illustrative sample of six previously prepared scripts contains 8,603 Unicode characters, averaging approximately 1,434 per video. Forty daily videos over thirty days would require approximately **1,720,600 characters** before any rework. Cloud recognition of forty 80–110-second videos daily would require approximately **26.7–36.7 audio hours/month**.

These are planning estimates, not account charges. They show that even a full unused published F0 allowance would not support this exact plan with the current voice path. Local recognition could replace the cloud recognition step only after validation; it does not provide free unlimited Nestoras synthesis.

No paid generation, top-ups, purchases, upgrades, unknown-price calls, alternate accounts/keys or unofficial quota workarounds are authorized. Existing provider credits are not a spending authorization.

### A working new program and exact final review

The new policy does not by itself implement or verify a production service. Legacy renderers are superseded and may not be reused to manufacture shared content. A current one-platform-per-story execution path must be validated before activation.

Every final video must be actually viewed and heard. `PASSED_FINAL_REVIEW` must identify the same media SHA256 that is delivered. A successful render, metadata or automatic transcript is insufficient by itself.

## Release sequence after the blockers are resolved

1. Verify the current policy and each platform's gate, actual zero-credit capacity, and restored authorized fresh-history access. Do not change global enablement merely because a timer ran.
2. Reconcile current live history, exact counts, leases and selected unique research ideas. New story selection must pass fresh duplicate review.
3. Prepare and verify factual source packs or clearly labeled original fiction, licensed scene plans, complete narration and accurate native metadata.
4. Render only through a verified zero-credit route. Listen to and inspect each exact final file, fix any material defect, and repeat review only as necessary.
5. Count already Published plus active Scheduled-PENDING for the relevant Athens date. Enforce the limit of ten per platform; never backdate or use withdrawn drafts to fill gaps.
6. Create exactly one target provider per new record. Read back brand, date, timezone, provider, media, draft/autoPublish flags, IDs/UUIDs and status after each write.
7. Maintain at least two complete future days per platform, with a target of three, only with real reviewed and scheduled media. Pending is not Published.
8. Report observed results and adjust the test mix using comparable evidence. Keep «Το μήνυμα που ερχόταν πάντα στις00:00» prepare-only.

## Verification boundaries

The repository dry-run only reads and prints legacy sample queue/plans. Passing that CI does **not** validate the new canonical strategy, exact media QA, account quotas or live queue readiness. The old `tools/check_rolling_queue.py` does not support the new program and must not be cited as its readiness certificate.

Current-head workflow holds do not prevent rerunning historical GitHub executions with old code. Such reruns must not be used while zero-credit capacity is unknown. No production workflow was dispatched as part of this change.

