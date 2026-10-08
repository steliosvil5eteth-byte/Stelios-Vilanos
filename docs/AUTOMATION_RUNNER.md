# Ενεργή οδηγία: διαφορετικά βίντεο ανά πλατφόρμα

Η νεότερη οδηγία της 08/10/2026 ορίζει **10 διαφορετικά βίντεο ανά πλατφόρμα/ημέρα, 40 διαφορετικές ιστορίες συνολικά**, στη μάρκα 7076410. Κάθε ιστορία έχει έναν μόνο προορισμό. Το μοναδικό authoritative αρχείο είναι `config/platform_growth_strategy.json`.

**Κατάσταση: BLOCKED_REQUIRED_HISTORY_AND_ZERO_CREDIT_CAPACITY.** Η παραγωγή και ο προγραμματισμός είναι απενεργοποιημένα. Δεν έχουν δημιουργηθεί ή προγραμματιστεί νέα βίντεο για αυτό το πρόγραμμα. Απαιτούνται επιτυχής εξουσιοδοτημένος fresh έλεγχος ιστορικού, επαλήθευση πραγματικής δωρεάν δυναμικότητας με μηδενικά credits, ελεγμένη νέα διαδρομή εκτέλεσης, και τελικός έλεγχος των ίδιων media.

Τα `CURRENT_TEN_DAILY` και `YOUTUBE_GROWTH_TEN_DAILY` είναι **SUPERSEDED**. Τα ιστορικά κείμενα παρακάτω δεν επιτρέπουν επαναφορά κοινών αναρτήσεων, παλιών sourcepacks ή παλιών παραγωγών. Η ενεργοποίηση του νέου config δεν ενεργοποιεί κάποιο παλιό workflow. Τα legacy Azure jobs έχουν τεθεί σε hold στο τρέχον head· παλιά commits/reruns δεν πρέπει να χρησιμοποιούνται.

Ο dry-run CI και το παλιό `tools/check_rolling_queue.py` δεν πιστοποιούν ετοιμότητα της νέας παραγωγής. Το νέο config περιγράφει πολιτική και στόχο, όχι ολοκληρωμένη υπηρεσία παραγωγής. Δες `docs/PLATFORM_SPECIFIC_TEN_DAILY.md` για τα gates και τη διαδικασία ελέγχου.

---

## Ιστορικό οδηγιών — ισχύει μόνο όπου δεν συγκρούεται με τα παραπάνω

# Automation Runner

Provider routing changed on 2026-10-08. The common program is governed by `config/content_strategy.json`; the independent YouTube program is governed by `config/youtube_growth_strategy.json`. Re-read the relevant strategy immediately before every write. A connected-network inventory is never a publishing allowlist.

## Sole active Metricool brand

- Brand: **Ιστορίες που μας αγγίζουν**
- Brand ID: **7076410**
- Timezone: **Europe/Athens**
- Common program providers: Facebook, Instagram and TikTok
- Independent YouTube program provider: YouTube only
- Previous Metricool brands are historical only and must never receive new writes.

## CURRENT_TEN_DAILY — common program

The existing ten required standing series, their content and formats remain unchanged for Facebook, Instagram and TikTok:

1. 07:00 — Relationships
2. 09:00 — Survival
3. 10:00 — Dog Bartender
4. 11:00 — Zodiac — **one carousel upload** containing six two-sign comparison units; all 12 signs appear exactly once in that carousel
5. 13:00 — Two-day trip in Greece
6. 15:00 — Love / Soul / Relationship
7. 17:00 — Strange real phenomenon
8. 18:30 — Documented experiments
9. 20:00 — Myth or Truth
10. 22:00 — International legend

These ten common logical posts produce **30 provider destinations per day**. YouTube is excluded. Never regenerate, refill or schedule a common YouTube adaptation to make this program appear complete.

`CURRENT_FIVE_DAILY`, `PARTIAL_SCHEDULED`, old five-slot ledgers, archived manifests and old queue snapshots are **never completion evidence**. They may be read only for history/deduplication. If records conflict with an active strategy, keep the affected work blocked until reconciled.

## YOUTUBE_GROWTH_TEN_DAILY — independent original videos

This program targets ten original narrated vertical YouTube videos per normal day, independently of the common ten posts. The selected profile in `config/youtube_growth_strategy.json` is `original_narrated_shorts`: 9:16, 1080x1920, at least 80 seconds, a target of 80–110 seconds and a maximum of 150 seconds, without filler or silence padding. It remains disabled until the actual batch is ready and reviewed. Do not silently relax duration, change narrator or exceed free capacity.

Focus on original human stories, sourced factual curiosities and history, and occasional folklore clearly labelled as folklore. Identify fictional stories as fiction.

Every YouTube item must have its own original script and media and explicit program attribution. Existing common scripts, carousel/slideshow adaptations and previously published stories do not count as new independent videos. Compare topic, hook, script, caption, fingerprint, episode/part and media identity across both programs and all historical sources.

On 2026-10-08, five already published YouTube videos count toward the daily total of ten. At most five additional new videos may be created that day. Refresh the live published and pending counts immediately before every create; simultaneous work can reduce this remaining capacity.

Normal-day combined targets after activation are **20 distinct logical items / 40 destinations**: ten common items to three providers and ten separate YouTube items. The ten-item limit is per program, not a combined limit.

## Provider isolation and transition

1. Cancel only unpublished legacy YouTube destinations after live readback confirms they are still unpublished.
2. For mixed records, remove only YouTube and preserve Facebook, Instagram and TikTok provider objects, dates, times, copy, media, draft and autoPublish settings.
3. Preserve all published history. Do not delete or rewrite published YouTube videos.
4. Keep the independent YouTube strategy disabled while its required configuration or delivery state is unresolved.
5. Exclude YouTube generation and publishing targets from the common 2026-10-09 manifest without changing its existing non-YouTube content or final media.
6. Update active automation and Notion routing too; GitHub rendering workflows are not the social publisher.
7. Never interpret cancellation of an old YouTube destination as permission to retry it.

## Mandatory program integrity barrier

Before any day is considered ready:

1. Re-read the selected strategy, its enabled state and provider allowlist.
2. Confirm brand 7076410, Europe/Athens, ten normal-day slots and the correct per-program destination count.
3. Build a program-specific slot matrix; apply the transition day's remaining allowance separately.
4. A slot is complete only when its exact final media passed direct final review and live Metricool readback confirms the intended provider state.
5. Missing, draft-only, stale-format, wrong-brand or legacy-state entries do not count.
6. Independent YouTube records require explicit program attribution and must not contain other providers.
7. If a slot misses its target time, never backdate. Repair it and use the first safe later time after fresh deduplication.
8. A blocker must name the concrete failing gate; it cannot be silently treated as completion.
9. `tools/check_rolling_queue.py` audits the selected strategy's providers and reports queue coverage only. Exact media QA, attribution and live reconciliation remain separate hard gates.

## Required media rules

Common card posts use distinct scene-relevant photographic/photorealistic visuals. TikTok uses native silent 1080x1080 photo assets with auto music where applicable. Facebook and Instagram use native carousels. Common card packs do not generate or publish YouTube adaptations.

Dog Bartender remains exactly four cards with the recurring photorealistic brown dog, visibly functioning as bartender, and a different composition on every card.

Common narrated slots retain 9:16 1080x1920 video, at least 80 seconds, **el-GR-NestorasNeural (Νέστορας)**, synchronized burned-in Greek subtitles, no avatar and no second music layer.

Independent YouTube duration and aspect ratio follow its selected format profile. Narrated YouTube videos use the same approved Nestoras voice and synchronized burned-in Greek subtitles, without an avatar or background music. Use only available free infrastructure; if the approved voice or free capacity is unavailable, block the affected video. No voice substitution, paid generation, top-up, upgrade, paid test or paid fallback is authorized.

## Publishing flow

1. Reconcile Metricool, Notion and repository/history for the selected program and all duplicate sources.
2. Fresh duplicate/history, strategy/provider and daily-cap check immediately before every create/update.
3. Render the exact final files from explicit scene-specific source files or URLs. Never replace a missing or failed source with a title-based pin, an automatic search result, or a broader query. Reject repeated source images within a carousel.
4. Visually inspect those exact files; metadata/render success is not QA.
5. Verify text, spelling, order, media relevance, crop, readability, CTA, caption, hashtags, duration, voice, subtitles, audio, platform format and AI disclosure.
6. Keep failed material Draft/Blocked.
7. Release only after **PASSED_FINAL_REVIEW**, bound to the exact final file hashes.
8. Write only to brand **7076410** and the selected program's providers.
9. After every write, live-read brand/date/time/providers/media/draft/autoPublish/IDs/UUIDs/status.
10. PENDING is not Published. Never blind-retry an unknown/partial write.

## Historical data

Old queue records, scripts, manifests and strategy files remain for audit/deduplication only. They must never be used to decide that an active program's day is complete or to restore a cancelled legacy YouTube destination.

