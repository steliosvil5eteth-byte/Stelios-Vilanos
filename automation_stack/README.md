# Social publishing control plane — STAGING ONLY

This folder is an **implemented, read-only stage**, not a working social publisher.
It follows `config/current_ten_daily.json` and does not supersede the separate `youtube_zodiac_20_daily` job.

## Safety locks

- No Metricool/Notion/GitHub credentials are copied from ChatGPT connectors into this environment. n8n credentials must be configured independently, with least privilege.
- The n8n workflow is **inactive** on import. Do not activate it concurrently with the existing ChatGPT automations (06:00 / 23:30), or identical checks may race.
- Worker only implements `GET /healthz` and read-only POST `/api/run`; every workflow execution returns `BLOCKED_MISSING_LIVE_CONNECTORS_AND_EXACT_FINAL_QA` until live reconciliation and final visual/audio inspection are implemented.
- **No endpoint for create, schedule, publish or retry exists.** Never equate `PENDING` with `PUBLISHED` or technical metadata check with `PASSED_FINAL_REVIEW`.
- User's active brand: 7076410. 10 logical daily posts, separate 20 YouTube Shorts.
- Narration MP4 is encoded **at 30 CFR from the initial render**, H.264/AAC; scene positions must be explicitly matched to voice. Final review remains `BLOCKED` until the exact exported MP4 is watched and listened to.
- No automatic upgrades, spending, generation calls or posts.

## Local staging prerequisites

Docker Engine, Compose v2, FFmpeg, a host that stays online, encrypted secrets storage, backups. Never run the management port publicly without a reverse proxy/TLS/auth. n8n official production hosting recommends persistent database and an encryption key. This compose binds the n8n editor to `127.0.0.1:5678` and persists its state locally. Do **not** deploy as-is on free Render: that tier spins down and has an ephemeral filesystem; not appropriate for a persistent scheduler.

```
cd automation_stack
cp .env.example .env
# replace BOTH passwords and choose audited pinned N8N_IMAGE

docker compose up -d --build
curl -sf http://localhost:5678/healthz
# Access editor on localhost:5678, import n8n/social_preflight.json.
# Keep workflow INACTIVE until migrating scheduling ownership from ChatGPT.
```

## Render an episode MP4 (independently usable)

Supply the narration and unique original **square** JPEG/PNG/WebP images in `episode_inputs/`. Create a scene manifest with exact speech-aligned start/end times, contiguous from 0 to narration duration. The example manifest uses placeholders and is not ready to run without matching 4-second narration and two photos.

```
python automation_stack/video_finisher.py \
  --manifest episode_inputs/manifest.json \
  --input-dir episode_inputs \
  --output episode_outputs/episode.mp4 \
  --report episode_outputs/episode.qa.json
```

For real episodes, the exact end time must match the audio file. The report includes SHA256, actual frames, decoding, codecs and durations. It **never** marks final review passed: technical verification cannot detect incorrect scene semantics, narration misalignment, poor Greek captions or issues with the actual voice. Those require viewing/listening to *the same exact final media*. Any QA correction must be rerendered and re-reviewed. Never publish from the report alone.

## Production gaps before hands-off operation

1. Durable always-on hosting with pinned version, TLS, backups; confirm price before provisioning.
2. Independent read-only credentials for Metricool, Notion, repository, and a reliable media store; use the published provider API only with suitable entitlement.
3. An atomic cross-system fingerprint lease/idempotency store: fresh history before every write, and live readback of provider status after it. GitHub history alone isn't a transactional lock.
4. Paid/free generation quotas and licensing verified for images, exact Nestor Greek voice and correct platform distribution. Avoid excess charges.
5. Real final-asset audio+visual review and scene timing validation, fail closed on missing evidence.
6. Safely migrate 06:00 and 23:30 check ownership; don't enable duplicate schedulers. Separate 20 YouTube Shorts remains intact.

## Test locally

```
python -m unittest discover -s automation_stack/tests -v
```

No live publishing is attempted by these tests.