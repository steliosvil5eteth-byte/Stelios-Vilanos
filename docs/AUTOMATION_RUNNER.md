# Automation Runner

This repository is the source of truth for the social-media queue.

## Connected mode

The current production path uses the user's connected ChatGPT plugins instead of storing API credentials in GitHub:

1. Read `queue/pending.json`.
2. Treat `job_id` as the primary job identifier. The legacy field `id` is still accepted for backwards compatibility.
3. Ignore any job whose identifier already exists in `queue/completed.json`.
4. Process at most the number configured in `config/integrations.json`.
5. If a job already contains `media_url` (or legacy `media`), skip generation.
6. If a job contains a HeyGen video id/status, use that state to decide whether generation is complete or still pending.
7. Schedule completed media through Metricool using brand `7000636`, timezone `Europe/Athens`, and only the platforms listed in the job.
8. Mark AI-generated content correctly on supported networks.
9. After successful scheduling, store returned Metricool post IDs/UUIDs and update the job status.
10. Never publish the same job identifier twice.

## Current queue job format

```json
{
  "job_id": "2026-09-18-zodiac-05-leo",
  "date": "2026-09-18",
  "theme": "zodiac",
  "zodiac_sign": "Λέων",
  "angle": "τι δεν συγχωρεί",
  "title": "Λέων — Τι δεν συγχωρεί",
  "caption": "Παράδειγμα caption",
  "hashtags": ["#Λέων", "#ζώδια", "#σχέσεις", "#fyp"],
  "heygen_video_id": "example-video-id",
  "media_url": null,
  "metricool_post_id": null,
  "metricool_uuid": null,
  "scheduled_time": "2026-09-18T14:00:00+03:00",
  "platforms": ["facebook", "instagram", "tiktok", "youtube"],
  "status": "heygen_processing"
}
```

## Backwards compatibility

The validator also accepts the original field names so older jobs remain valid:

- `id` → `job_id`
- `networks` → `platforms`
- `scheduled_at` → `scheduled_time`
- `media` → `media_url`

## Statuses

Expected lifecycle examples include:

- `pending`
- `processing`
- `heygen_processing`
- `scheduled`
- `published`
- `failed`

## Safety

- Duplicate protection is keyed by `job_id` or legacy `id`.
- A job with a past schedule must not be published automatically; it must be rescheduled to a future time.
- Missing media/generation prerequisites cause the job to remain pending rather than publishing incomplete content.
- GitHub files contain configuration and state only; authentication remains in connected services or secure secrets.
- Do not place passwords, tokens, cookies, API keys or private credentials in queue files.
