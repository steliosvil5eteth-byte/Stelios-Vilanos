# EXECUTION QUEUE — Social Control Center
Updated: 2026-10-28. Owner: user. Mode: SAFE / no live execution.

## Completion criteria
Do not declare COMPLETE until a **single** canonical story passes all gates: complete source script, originality check against complete Notion history, 16 distinct 1080×1080 images with individual visual QA, natural Greek narration with measured timestamps, synced MP4 with watched/listened QA, rights and cost check, and provider readback before any publishing. Then verify all ten-slot daily planning and cross-brand duplicate prevention. Any missing evidence = BLOCKED.

## Next executable tasks, ordered
1. [IN_PROGRESS] Story 01 only: validate actual source narration, character bible, 16 scene map. Reject unrelated funeral/collage/sea scenes.
2. [BLOCKED_MEDIA] Render scene 02 as **one independent full-resolution image**; verify its narrative match and dimensions. Continue scenes 03–16 sequentially, not in a composite. Current count: scene 01 candidate only, **0 approved**.
3. [BLOCKED_AUDIO] Replace robotic Greek draft with a natural-quality voice, without paid credits; measure real audio timings.
4. [BLOCKED_HISTORY] Complete Notion archive including archived entries; never treat a partial archive as complete.
5. [PENDING] Render final MP4 and manual audiovisual QA; no live publication until approved.
6. [PENDING] Repeat process for story 02 only after story 01 passes.
7. [PENDING] Build and verify ten-slot daily workflow, Metricool/Notion readback across both brands, no duplicate retries.
8. [BLOCKED_AUTONOMY] No available additional scheduled-task slot; no background continuation can be claimed. User may authorize modifying one existing automation, but no automatic replacement.

## Operating rules
- At each actual invocation, select highest-priority executable task; persist evidence and blockers after each meaningful action.
- Never call a script or image complete based solely on a generated collage, metadata, caller-provided booleans, or passing unit tests.
- Never silently consume paid credits, subscribe, modify live automations, publish, or delete content.
- Work on isolated branch `new-system/control-center-v1`; preserve `main`.
- If a step cannot be completed with current tools, record the exact failure and advance to an independent safety/infrastructure task, **not** another story.
- This file is a persistent queue, **not** a running agent. Actual work requires an active conversation, automation slot, or separately deployed worker.

## Current verified evidence
- GitHub `FIRST_STORY_SCENE01_QA.md`, `FIRST_STORY_GATE_V13.md`, `FIRST_STORY_CANONICAL_QA.md` document story mismatch and image rejections.
- Metricool 2026-10-28 readback: 3 main-brand posts, 0 second-brand posts for that day only; TikTok confirmation pending for one.
- Notion 291 active rows examined; archived coverage unverified.
- Offline drafts, robotic WAV previews and placeholder MP4 are **not release-ready**.

## GitHub Actions improvement — 2026-10-28
- Added `.github/workflows/new-system-audit.yml` on isolated branch, triggered on branch pushes affecting `new_system/**` and by manual dispatch.
- Runs offline Python unittest discovery and checks sample manifest does not enable publishing. No external provider actions or credentials.
- **Execution result not yet verified**; do not call the workflow passing until its run is inspected.
- GitHub scheduled workflows require default-branch presence; this branch-only workflow is not an always-on scheduled worker.
