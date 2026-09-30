# Automation Runner

This repository follows exactly one operational social-media strategy: `config/content_strategy.json`.

## Sole active Metricool brand

- Brand: **Ιστορίες που μας αγγίζουν**
- Brand ID: **7076410**
- Timezone: **Europe/Athens**
- Networks: Facebook, Instagram, TikTok, YouTube
- Previous Metricool brands are historical only and must never receive new writes.

## CURRENT_TEN_DAILY — sole active schedule

The active schedule contains ten required standing series:

1. 07:00 — Relationships
2. 09:00 — Survival
3. 10:00 — Dog Bartender
4. 11:00 — Zodiac — **bundle of 6 separate member posts**, each comparing exactly 2 signs in 4 cards; all 12 signs appear exactly once per daily bundle
5. 13:00 — Two-day trip in Greece
6. 15:00 — Love / Soul / Relationship
7. 17:00 — Strange real phenomenon
8. 18:30 — Documented experiments
9. 20:00 — Myth or Truth
10. 22:00 — International legend

`CURRENT_FIVE_DAILY`, `PARTIAL_SCHEDULED`, old five-slot ledgers, archived manifests and old queue snapshots are **never completion evidence**. They may be read only for history/deduplication. If they conflict with `config/content_strategy.json`, the active strategy wins and publication stays fail-closed until reconciled.

## Mandatory 10-slot integrity barrier

The ten standing series produce **exactly 10 baseline uploads per network / 40 destinations per day**. The 11:00 Zodiac standing series is one upload: a single carousel containing six two-sign comparison units that cover all 12 signs exactly once. Splitting Zodiac into six separate uploads is forbidden.

Before any day is considered ready:

1. Re-read `config/content_strategy.json`.
2. Confirm strategy_id starts with `CURRENT_TEN_DAILY`, brand is 7076410 and exactly ten standing slots are active.
3. Build a ten-slot matrix for the local date.
4. A slot is complete only when the exact final media passed direct final review and live Metricool readback confirms the intended state.
5. Missing, draft-only, stale-format, wrong-brand or legacy-state entries do not count.
6. Never stop production because an older five-slot manifest says SCHEDULED/PASSED.
7. If a slot misses its target time, never backdate. Repair it and use the first safe later time after fresh deduplication.
8. A blocker must name the concrete failing gate; it cannot be silently treated as completion.

## Required media rules

Card posts use distinct scene-relevant photographic/photorealistic visuals. TikTok uses native silent 1080x1080 photo assets with auto music where applicable. Facebook and Instagram use native carousels. YouTube uses the complete ordered card set in a vertical slideshow with one permitted instrumental layer.

Dog Bartender uses the recurring photorealistic brown dog, visibly functioning as bartender, with a different composition on every card.

Narrated slots use 9:16 1080x1920 video, at least 80 seconds, **el-GR-NestorasNeural (Νέστορας)**, synchronized burned-in Greek subtitles, no avatar and no second music layer.

## Publishing flow

1. Reconcile Metricool, Notion and repository/history.
2. Fresh duplicate/history check immediately before every create/update.
3. Render the exact final files.
4. Visually inspect those exact files; metadata/render success is not QA.
5. Verify text, spelling, order, media relevance, crop, readability, CTA, caption, hashtags, duration, voice, subtitles, audio, platform format and AI disclosure.
6. Keep failed material Draft/Blocked.
7. Release only after **PASSED_FINAL_REVIEW**.
8. Write only to brand **7076410**.
9. After every write, live-read brand/date/time/providers/media/draft/autoPublish/IDs/UUIDs/status.
10. PENDING is not Published. Never blind-retry an unknown/partial write.

## Historical data

Old queue records and strategy files remain for audit/deduplication only. They must never be used to decide that a CURRENT_TEN_DAILY day is complete.
