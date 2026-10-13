# Read-only archive collection and the remaining host boundary

Scope: policy-neutral reader, refreshed against live `main` at `8cb58d01bfea45e234189f79e10bbbb1a566c579` on 2026-10-14 Europe/Athens (2026-10-13 UTC). This patch adds one executable reader. It does not change cadence, activate release flags or deploy an unattended publisher. The initial Oct10 audit against `18c520a0a636b29d8415fb2ad2bb0e504425a117` is historical.

## Current policy and implementation mismatch

The freshly read canonical configuration, blob `b3c50ddbf9820792d719fd9048335396519c072c`, now specifies **15 distinct videos total, cross-posted to four platforms: 60 provider destinations**. It records a later instruction at 2026-10-10 20:39 +03:00 and a subsequent cadence revision. That underlying conversation was not independently available in this audit; the newer existing policy is preserved. The earlier 60-distinct-video assumption must not overwrite it.

The current core has not implemented that newer sharing model: `production_errors()` still expects 60 distinct stories and videos; `validate_manifest()` rejects shared story/script/media identities across all 60 delivery jobs; the publisher journal has global unique story/media/fingerprint/script keys and treats another provider's use of the same asset as an existing attempt. `config/integrations.json` also still says `crossposting_allowed:false` and describes sixty distinct videos. This is an additional release blocker, not permission to weaken duplicate protection. A separate reviewed policy-alignment change would need explicit story-versus-delivery identities and safe cross-platform deduplication. It is outside this reader patch.

The reader imports no cadence code and neither inspects nor rewrites these targets. Current canonical enabled/active-schedule/production flags and the integration runner's production/publication flags are false.

## What this patch implements

`notion_archive.collect_archive(call_tool)` accepts the same synchronous authenticated host-callback shape used by the Metricool adapter. Its dispatch is limited to `mcp__codex_apps__notion_fetch` and `mcp__codex_apps__notion_query_data_sources`.

The pinned source is `collection://46cd5cf4-5f7e-46e8-b0ef-274aeadbdb52`; the pinned Default view is `view://9200bc65-1a99-4479-b680-df8aedba0e6b`. The reader first fetches the actual schema and view, requires that the view belongs to that source, has no filter and displays every schema property, then consumes **both active and archived** row pagination. Each partition retains its own cursor state. Empty intermediate pages do not terminate the read. Repeated cursors, duplicate page identities, partial responses, malformed pagination and configured resource bounds stop the operation without returning partial completion. The schema and view are fetched again at the end; changes also stop the operation.

The implementation follows the connected-tool shapes observed on 2026-10-10: fetch returns enhanced-Markdown entity text in `structuredContent`; the view query returns a JSON object in `content[0].text` with `results`, `has_more` and `next_cursor`. Query rows are flat property dictionaries with a `url`, rich text and expanded date-property keys. Unknown query-envelope settings fail closed. Only saved-view mode is used; there is no SQL retry or paid-mode fallback.

Rows are preserved exactly. The output includes the start/end read times, page counts, row count and SHA-256 hashes of the schema, view and collected rows. It deliberately states `atomic_snapshot:false` and `release_clearance:false`. `pagination_exhausted:true` means that this sequence of reads consumed the cursors; it does not prove an atomic snapshot while other actors may change the archive. Permanently deleted or inaccessible content is outside what the connector can enumerate.

**The output is not a `publisher.schedule_once()` history receipt.** It does not provide `status`, `complete`, `expires_at`, `observed_delivery_keys`, QA approval or lease evidence. A host must coordinate concurrent changes and join the real external evidence before it can create those receipts. Raw archive rows should remain in the host's private evidence storage; this module neither writes them to disk nor uploads them to a repository.

## Pieces still absent from the audited implementation

| Boundary | Already implemented | Still required |
|---|---|---|
| Authenticated tool execution | `publisher.MetricoolConnectorTransport` sends the observed connector arguments; the new reader sends supported Notion read arguments. | A real host callback bound to an authorized connected-tool session. The modules do not discover credentials, perform login or supply a background authentication service. |
| Fresh multi-source refresh | `publisher.validate_refresh_evidence` requires new, individually fresh source and queue receipts for each attempted create. This patch implements raw Notion pagination. | Complete Metricool and repository history collection, a current queue count, cross-source identity matching, concurrent-change coordination and the actual `refresh()` callback. |
| Reconciliation | `publisher.require_journal_reconciled` blocks unresolved writes and requires prior delivery keys in all three archives and current-day queue counts. | Writers/readbacks that update the existing Notion and repository records from actual provider IDs/UUIDs/status, and derive acknowledgments from those durable records. Unknown writes require investigation; there is no retry/replay path. |
| Shared journal | SQLite durable claims, unique story/media/fingerprint/normalized-script keys, a filesystem lock and binding validation exist. | Provisioning and verification that every executor uses the same private durable physical store. Identical path strings on different hosts are insufficient. |
| Exclusive production lease | Core preflight verifies the supplied lease and current executor bindings. | Authoritative acquire/renew/release, expiry and compare-and-swap ownership handling across all executors. The Oct9 completed manual lease is historical evidence only. |
| Unattended launch | `schedule_once(..., execute=False)` is callable; the workflow runs local validation/plan generation. | A supervised execution entry point, authenticated runtime, job selection and reconciliation loop. No activated daily production schedule is supplied by this patch. |
| Release prerequisites | The existing guards enforce exact final-media QA, cost evidence, allowed routing/time, native disclosure and the 15-per-platform cap. | Current proof of Azure allowance, actual final audio listening and visual review, verified native Facebook disclosure support, reviewed staged bytes and operational host/lease bindings. Code cannot manufacture these facts. |

After resolving the documented policy/code mismatch in a separate reviewed change, the minimal host work should bind **one** verified host to the adapter and shared store, implement full evidence collection and durable reconciliation, and exercise read-only recovery with recorded failures before any release activation. Adding a second scheduler, a guessed authentication protocol or declarative approval JSON would not close those boundaries.

## Source audit

- [Current canonical policy](https://github.com/steliosvil5eteth-byte/Stelios-Vilanos/blob/8cb58d01bfea45e234189f79e10bbbb1a566c579/config/platform_growth_strategy.json): 15 distinct videos, allowed sharing across four platforms, 60 destinations; disabled release flags.
- [Current publisher](https://github.com/steliosvil5eteth-byte/Stelios-Vilanos/blob/8cb58d01bfea45e234189f79e10bbbb1a566c579/production/platform_specific/publisher.py): `MetricoolConnectorTransport`, `validate_binding`, `validate_refresh_evidence`, `require_journal_reconciled`, `schedule_once`; global identity uniqueness in `connection()` and `known_attempt()`.
- [Current core](https://github.com/steliosvil5eteth-byte/Stelios-Vilanos/blob/8cb58d01bfea45e234189f79e10bbbb1a566c579/production/platform_specific/pipeline.py): policy, history, lease and release gates; obsolete 60-distinct assumptions described above.
- [Current integration configuration](https://github.com/steliosvil5eteth-byte/Stelios-Vilanos/blob/8cb58d01bfea45e234189f79e10bbbb1a566c579/config/integrations.json): disabled runner, read-only inventory/local validation allowlist and stale prohibition of cross-posting.
- [Current dry-run workflow](https://github.com/steliosvil5eteth-byte/Stelios-Vilanos/blob/8cb58d01bfea45e234189f79e10bbbb1a566c579/.github/workflows/platform-specific-dry-run.yml): manual validation/plan job, without a production scheduler.

The following supporting files were inspected in the earlier Oct10 audit; they are historical source references, not fresh Oct14 operational evidence:

- [Legacy queue auditor](https://github.com/steliosvil5eteth-byte/Stelios-Vilanos/blob/18c520a0a636b29d8415fb2ad2bb0e504425a117/tools/check_rolling_queue.py): local supplied snapshots and retired ten-slot labels; not the current refresh callback.
- [Historical release packager](https://github.com/steliosvil5eteth-byte/Stelios-Vilanos/blob/18c520a0a636b29d8415fb2ad2bb0e504425a117/production/platform_specific/package_completed_release.py): Oct9/40-item packaging; not live archive reconciliation.
- [Legacy entry point](https://github.com/steliosvil5eteth-byte/Stelios-Vilanos/blob/18c520a0a636b29d8415fb2ad2bb0e504425a117/src/pipeline.py): rejects live mode.
- [Oct9 lease](https://github.com/steliosvil5eteth-byte/Stelios-Vilanos/blob/18c520a0a636b29d8415fb2ad2bb0e504425a117/state/production_leases/2026-10-09-brand7076410.json): expired `COMPLETED_MANUAL_RECOVERY`; no current global automation activation.

This is a source-level conclusion. An external deployed service cannot be inferred from these files and has not been authenticated or verified by this patch.

## Verification

Run from the repository root:

```sh
PYTHONPATH=production/platform_specific python -m unittest discover -s production/platform_specific/tests -p 'test_notion_archive.py' -v
```

All 14 focused tests passed again on the Oct14 Athens review, including the root reviewer's separate rerun. The root reviewer also fetched the pinned collection and view afresh and successfully ran `schema_from(payload(...))` and `view_from(...)` against the exact native envelopes: 62 schema fields, all displayed, and no view filter. The private live-envelope fixture is excluded from this three-file patch and must not be committed. Query pagination was originally observed on Oct10; no new row query, full archive scan or live host execution was performed in the Oct14 review.

Test fixtures are explicitly synthetic and contain no real post records or approval evidence. No credentials, generation, media staging, provider create, policy change, external write or deployment was performed for this patch. The existing production and publishing flags remain unchanged and disabled. No historical readiness report was edited; a new operational report belongs at `state/daily_recovery_20261014.json`.
