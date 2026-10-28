# New System — Control Center v1

Isolated development branch: `new-system/control-center-v1`. Existing `main` workflows and publishing remain untouched.

## Scope
Daily plan: five distinct emotional stories; one fictional Greek myth; one zodiac video; one comparison; one Greece today vs two years ago; one verified name-day greeting. Total 10 distinct videos. No paid services.

## Run
`python3 new_system/control_center.py new_system/sample_manifest.json`

The sample intentionally fails closed because no items or QA evidence are provided. Exit code 1 means blocked; 0 means review-ready **not published**. Uses only Python standard library. No network, GitHub Actions, scheduled jobs, API keys, or publishing endpoints. No files are modified by execution.

## Manifest item fields
Each item must have `id`, `category`, `title`, `opening`, `ending`, `plot_key`, `source_status`, `qa_status`, and `cost_eur`. Fictional myths also need `fiction_disclosure:true`. `source_status:verified` is required for factual videos. The three manifest-wide gates are `history_checked`, `calendar_verified`, `manual_review_confirmed`.

## Safety limitations
Uniqueness detection currently catches exact normalized duplicate titles, openings, endings, and plot keys *within the manifest*. It does not yet prove semantic uniqueness or search historical posts; history checking requires a verified external reconciliation step. Source verification and QA are human-provided flags, not independently validated. A review-ready result is **never** permission to publish. Future automation and connector integration require a separate approval.
