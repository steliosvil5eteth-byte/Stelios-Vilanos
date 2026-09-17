# Automation Runner

This repository is the source of truth for the social-media queue.

## Connected mode

The current production path uses the user's connected ChatGPT plugins instead of storing API credentials in GitHub:

1. Read `queue/pending.json`.
2. Ignore any job whose `id` already exists in `queue/completed.json`.
3. Process at most the number configured in `config/integrations.json`.
4. If a job already contains a public `media` URL, skip generation.
5. If a job contains `generator: "heygen"`, generate the video through HeyGen only when the required presenter/generation prerequisites are satisfied.
6. Schedule the completed media through Metricool using brand `7000636`, timezone `Europe/Athens`, and only the networks listed in the job.
7. Mark AI-generated content correctly on supported networks.
8. After successful scheduling, move the job from pending to completed and store any returned post IDs/UUIDs/URLs.
9. Never publish the same job ID twice.

## Queue job format

```json
{
  "id": "funny-2026-09-17-001",
  "status": "pending",
  "title": "Example funny short",
  "caption": "Example caption",
  "hashtags": ["χιουμορ", "αστεια"],
  "scheduled_at": "2026-09-17T21:00:00+03:00",
  "networks": ["facebook", "instagram", "tiktok", "youtube"],
  "media": "https://public.example/video.mp4"
}
```

For generated media, replace `media` with a generator configuration. Do not place passwords, tokens, cookies, API keys or private credentials in queue files.

## Safety

- Duplicate protection is keyed by `id`.
- A job with a past schedule must not be published automatically; it must be rescheduled to a future time.
- Missing media/generation prerequisites cause the job to remain pending rather than publishing incomplete content.
- GitHub files contain configuration and state only; authentication remains in connected services or secure secrets.
