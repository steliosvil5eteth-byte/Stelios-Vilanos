# Platform-specific narrated-video production

This is a new local orchestration path for **forty different stories per Athens
day: ten each for Facebook, Instagram, TikTok and YouTube**. It does not reactivate
the retired shared `CURRENT_TEN_DAILY` program. Every job has one platform string;
broadcast provider arrays, repeated story IDs, fingerprints, titles and script
bodies are rejected across the whole day.

The code is intended for `production/platform_specific/` in the repository.
Daily editorial inputs belong in `production_20261009_platform_specific/` (and
the corresponding date directory). Private account receipts, archive extracts,
credential fingerprints and usage ledgers **must remain outside the public
repository**. Do not commit them or print them to Actions logs.

## What is implemented

* `pipeline.py`: 40-slot scaffold; actual source-pack import; structural and
  identity validation; honest stage/blocker report; fresh complete history and
  exclusive-lease checks; conservative cumulative budget planning; exact-file
  review gate; one-job release handoff with a live daily platform cap.
* `synthesize_guarded.py`: one optional Azure Speech attempt, only after every
  production, source, history, budget and credential-binding gate passes. SDK
  import occurs only inside the provider adapter. The executor must bind the
  resolved ledger path, resource and billing period to its verified private
  lease. Atomic persistent reservations in that shared store prevent double
  spending; an uncertain attempt stays reserved. No fallback,
  voice substitution, account rotation, automatic retry or duration resynthesis.
* `render_local.py`: actual local FFmpeg rendering from an existing exact WAV,
  timed SRT and reviewed portrait scenes. It preserves speech speed and complete
  content, uses no background music/avatar, and produces H264/yuv420p 30fps
  1080x1920 MP4, AAC mono 48kHz, faststart, measured Greek subtitle wrapping,
  visible AI disclosure, and review frames for every subtitle cue and scene.
* `tests/`: failure-focused tests for identity, history errors, credential
  mismatch, quota races/lag, exact-byte review invalidation, real-media probing,
  platform/day capacity, subtitle loss and disabled-path zero provider calls.

There is **no publisher here**. A handoff is neither a scheduled post nor a
publication. An authorized operator must use the supported publishing connector,
verify its native disclosure setting, and record live provider readback after
each write. The next job requires a new queue snapshot. No bundled workflow
executes synthesis, rendering or publication automatically.

## Current operational limits

The copied reference policy remains disabled. There is no verified current
Azure SKU/free-allowance receipt, successful complete current archive receipt,
actual final audio review, or provider write approval manufactured by this code.
Templates deliberately fail closed. A source pack and an empty slot both count
as **zero** scheduled queue items. `plan` always reports real queue count zero
because it has not performed a live publishing readback.

The pipeline has been tested locally; the actual Azure SDK/network execution
path has not been exercised. Actual voice/pronunciation, narration completeness,
subtitle synchronization, and visual quality still need a real reviewer of each
exact final MP4. Technical decode/metadata and contact sheets cannot perform that
review. No function fills the human review booleans with `true`.

## Local requirements and commands

Linux, Python 3.10+, Pillow, FFmpeg/ffprobe with libass, and
`/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf` are required for media work.
The tested environment was Python 3.12.14, Pillow 12.3.0, FFmpeg 6.1.1. The Azure
Speech SDK is optional and needed only for a separately authorized future live
synthesis attempt; it is not imported by planning/tests/local rendering.

From the repository root:

```sh
python production/platform_specific/pipeline.py scaffold \
  --date 2026-10-09 \
  --output production_20261009_platform_specific/manifest.json

python production/platform_specific/pipeline.py import-catalog \
  --manifest production_20261009_platform_specific/manifest.json \
  --catalog production_20261009_platform_specific/catalog.json \
  --output production_20261009_platform_specific/manifest.json

python production/platform_specific/pipeline.py plan \
  --manifest production_20261009_platform_specific/manifest.json \
  --policy config/platform_growth_strategy.json \
  --output production_20261009_platform_specific/plan.json

cd production/platform_specific
python -m unittest discover -s tests -v
```

The scaffold uses the original initial test slots, without claiming optimal
performance. The integrator can assign fresh platform-specific test times before
validation; each platform must retain ten unique local times. A separate manifest
is required for each date. Catalog entries with another explicit date are not
silently reassigned to tomorrow.

Source packs contain `id` or `story_id`, `platform`, `local_date`, `title`,
`fingerprint`, complete `script`, `caption`, `kind`, `sources`, and optionally
`hook`/`scene_beats`. Valid kinds are `fiction`, `folklore`, `documented`, `science`,
`travel`, and `entertainment`. Factual kinds need sources. The exact spoken CTA
must end the script: «Αν σας άρεσε, ακολουθήστε για περισσότερα.» Captions permit
at most five hashtags. Importing a catalog intentionally does not import a QA
pass flag. `source_review` must bind `passed`, reviewer and `story_sha256` to the
exact title/script/caption/sources reviewed, using `pipeline.story_hash(job)`.

## Private prerequisites

Pass real private receipt files with `--history` and `--budget` to `plan` when
available. The examples in `contracts/` are **invalid placeholders**, not approvals.

History requires timezone-aware `checked_at`/`expires_at`, `complete: true`, and
successful complete reads from `metricool`, `notion`, `repository`, and
`production_lease`. Metricool, Notion and repository reads need positive
`rows_seen`. The checked story archive must be nonempty; nested API errors block
even when an outer status says success. Exact identity matches block, and each
job additionally requires a fresh semantic-review clearance bound to its story
hash. A missing archive or rate-limit error cannot become an empty clean list.
Execution additionally requires an owned, unexpired lease for brand 7076410,
the exact date and the specific action. A preparation-only lease cannot permit
synthesis, rendering or release just because it has no conflict.

Before a release, a separate queue snapshot must be at most five minutes old,
complete, for brand 7076410, the exact Athens date and chosen platform. Existing
`published + active_pending` must be below ten. Inactive drafts and failed rows
do not count as active pending. The manifest's ten slots do not replace this
live capacity check.

An Azure receipt must come from an authorized live management/account read and
confirm the actual resource ID, **actual F0 SKU**, zero cost, complete current
period usage, provider-observed remaining TTS characters, evidence digest and
reviewer. A generic Azure welcome email, a public F0 allowance, an environment
variable name or `azure_speech_f0` string is insufficient. Each job also needs a
reviewed conservative `tts_charge_upper_bound` covering its provider billing
units; a raw character estimate is not account evidence.

The receipt's private `credential_binding` must bind that **same resource** to
the exact current key fingerprint, region and endpoint. Before any SDK call the
adapter compares it with a private immutable snapshot of the environment key and
region. Neither the key nor its hash is printed. Missing or mismatched binding
blocks even if a different resource's receipt says F0.

Use one shared durable private ledger and exclusive production lease. Do not copy
the ledger independently to parallel workers. Before reserving or calling the
provider, the adapter requires `production_lease.executor_binding` with private,
reviewed evidence of the shared durable store. Its `ledger_path` must be absolute
and resolve to the supplied ledger path; `resource_id` and `period` must match the
Azure receipt, and `executor_id` must match the lease owner. It also requires
`verified_shared_durable_store: true`, reviewer, a SHA256 evidence digest and
fresh timezone-aware `checked_at`/`expires_at` (at most fifteen minutes old).
No example in this repository supplies a valid operational binding.

These path checks do not prove that different hosts use the same filesystem.
Copying this code or using the same path string on a second host still requires
one common durable store and coordinated executor/lease; independent copies
cannot safely share an allowance. A verified binding must reflect the actual
storage arrangement, not merely the intended path.

CONSUMED reservations remain
counted despite a newer receipt timestamp because Azure usage may lag. They are
removed from extra reservation accounting only when the receipt explicitly lists
their `included_attempt_ids` and its `usage_window_end` covers their recorded
completion. RESERVED and UNKNOWN attempts always remain counted. Errors stop the
job without automatic retry. Reconciliation/revision needs a deliberate new
decision and fresh evidence; deleting a ledger is not a retry mechanism.

The one-job synthesis CLI also requires explicit `--execute`; omitting it makes
zero calls. The canonical policy, global production and selected platform must
all be enabled by a separately authorized integration; this code never flips
those flags. The helper emits `nestoras.wav`, `boundaries.json`, `script.txt`,
`subs.srt`, and an `audio.json` record with exact hashes and actual listening false.
Out-of-range duration stops after that measured attempt; it is never padded or
resynthesized automatically.

## Render and exact-final review

Attach an `audio` record to a job with local `path`, `sha256`, `srt_path`,
`srt_sha256`, exact `script_sha256`, `voice`, and `background_music: false`.
Attach at least four distinct single-photo portrait `scenes`. Each needs local
`path`, `sha256`, contiguous `start`/`end` seconds covering the complete narration,
reviewer, rights and relevance confirmation, `photographic: true`,
`contains_child_face: false`, and `contains_avatar: false`. Optional crop focus
coordinates are in [0,1]. Scene review also binds `story_sha256` to the exact
story, so changing the script requires relevance to be reviewed again. The renderer uses static crops; it never creates scene
images or repeats them to reach duration.

```sh
python production/platform_specific/render_local.py \
  --manifest production_20261009_platform_specific/manifest.json \
  --job-id 2026-10-09-youtube-01 \
  --policy config/platform_growth_strategy.json \
  --history /private/approved-history.json \
  --output /private/media/2026-10-09-youtube-01
```

It refuses to overwrite an existing output directory. Source audio must be mono
and 80–110 seconds. It rejects excessive dead air, missing or changed subtitle
words, overlapping timings, unreadable measured subtitle lines and incomplete
scene timelines. The only subtitle timing adjustment combines an exactly
matching trailing CTA into one complete displayed cue. Narration is not changed.

The final technical report is bound to job, platform, story hash and MP4 SHA256.
The pending review template remains false until a real reviewer records every
required check, including actual complete listening and confirmed Nestoras voice.
Both render creation and completed review must be in the past or present, with
`created_at <= reviewed_at <= now`; a future timestamp cannot clear the gate.
Attach exact paths/hashes for the video, technical report and completed review
to the job's `final` record. Any changed byte invalidates the prior binding. A
release preflight independently probes the actual video bytes again and validates
format/duration; a `technical_passed` label cannot override an invalid container.

```sh
python production/platform_specific/pipeline.py export-release \
  --manifest production_20261009_platform_specific/manifest.json \
  --job-id 2026-10-09-youtube-01 \
  --policy config/platform_growth_strategy.json \
  --history /private/fresh-history-and-queue.json \
  --output /private/release-one-job.json
```

This creates at most one handoff with an idempotency key, future time, one
platform, exact media hash and reviewed caption. It performs **no publication**.
Native AI disclosure must have supported-platform evidence, and the final transport
still needs live readback before any status may become Scheduled or Published.
