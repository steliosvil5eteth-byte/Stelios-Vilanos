# Automation Runner

This repository is the source of truth for the current social-media workflow.

## Sole active Metricool brand

- Brand: **Ιστορίες που μας αγγίζουν**
- Brand ID: **7076410**
- Timezone: **Europe/Athens**
- Networks: Facebook, Instagram, TikTok, YouTube
- Previous Metricool brands are **retired from operational use**. Do not schedule, publish, repair, reconcile, or create new posts on them.

## CURRENT_TEN_DAILY

Exactly 10 logical posts are targeted per day:

1. 07:00 — Relationships — 7-card carousel
2. 09:00 — Survival — 9-card carousel
3. 11:00 — Zodiac — 6-card carousel
4. 13:00 — Brown Dog Bartender — 4-card carousel
5. 15:00 — Love / Soul / Relationship — 5-card carousel
6. 17:00 — Strange real phenomenon — narrated vertical video
7. 18:30 — Two-day trip in Greece — narrated vertical video
8. 20:00 — Myth or Truth — 4-card carousel
9. 21:30 — Documented experiments — narrated vertical video
10. 23:00 — International legend — narrated vertical video

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

The planned clock time is a target, not permission to publish bad material. If a slot fails or is not ready, keep it Draft/Blocked, repair it, run full QA again, and publish it later the same day at the first safe available time. Never backdate. Before retrying, live-check that it did not publish on any destination. The end-of-day target is exactly **10 correct logical posts**, not 9 because a time was missed and not 11 because of a duplicate catch-up.

## Historical data

Old queue records, completed posts and previous brand references may remain in repository history for audit/deduplication. They are not active routing instructions.
