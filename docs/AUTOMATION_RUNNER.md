# Automation Runner

This repository is the source of truth for the current social-media workflow.

## Sole active Metricool brand

- Brand: **Ιστορίες που μας αγγίζουν**
- Brand ID: **7076410**
- Timezone: **Europe/Athens**
- Networks: Facebook, Instagram, TikTok, YouTube
- Previous Metricool brands are **retired from operational use**. Do not schedule, publish, repair, reconcile, or create new posts on them.

## CURRENT_FIVE_DAILY

Effective 27 September 2026: one post per active series, five logical posts per day across four networks.

1. 09:00 — Survival — 9 cards
2. 11:00 — Zodiac — 6 cards
3. 15:00 — Love / Soul — 5 cards
4. 17:00 — Strange real phenomenon — narrated video
5. 20:00 — Myth or Truth — 4 cards

Paused: separate 07:00 relationship commentary, dog bartender, Greece trips, experiments and legends. Never create or catch up paused series. Keep their files and published history. The current config/content_strategy.json takes priority over any older manifest or automation. Re-read it immediately before every scheduling write.

Selection: mean TikTok views per post, 20–25 September, all over 24 hours old. Small unequal samples; phenomena depend heavily on Brinicle. See selection_evidence in the strategy. No guarantee of future performance.

## Required media rules

Card posts use scene-relevant photographic/photorealistic visuals. TikTok uses silent 1080x1080 JPEG/WebP cards with native auto music. Facebook and Instagram use native carousels. YouTube uses the complete ordered card set in one vertical slideshow with one original instrumental layer and no narration.

Zodiac cards must visibly show the corresponding sign's own image/symbol/visual identity. Plain black or text-only zodiac panels are blocked.

Dog Bartender must use the same recurring **brown photorealistic dog bartender** in all four cards, clearly visible as the bartender in a believable real bar, with a distinct composition in every card.

Narrated slots use 9:16 1080x1920 video, at least 80 seconds, **el-GR-NestorasNeural (Νέστορας)**, synchronized burned-in Greek subtitles, no background music, no avatar/presenter and no filler or silence padding.

## Publishing flow

1. Build the logical post.
2. Check published-history deduplication.
3. Render the exact final media.
4. Inspect the exact final cards/video, not just filenames or metadata.
5. Verify format, order, visuals, audio, subtitles, duration, CTA, sources/licenses and AI disclosure where applicable.
6. Before final QA keep Metricool as draft=true and autoPublish=false.
7. Release only after **PASSED_FINAL_REVIEW**.
8. Schedule only on brand **7076410**.
9. After a successful write, live-read Metricool and store the returned post ID/UUID.
10. Never publish the same logical post twice.

## Quality-first catch-up

The planned clock time is a target, not permission to publish bad material. If a slot fails or is not ready, keep it Draft/Blocked, repair it, run full QA again, and publish it later the same day at the first safe available time. Never backdate. Before retrying, live-check that it did not publish on any destination. The end-of-day target is five correct logical posts, one per active series. Never fill retired slots or duplicate successful posts.

## Historical data

Old queue records, completed posts and previous brand references may remain in repository history for audit/deduplication. They are not active routing instructions.
