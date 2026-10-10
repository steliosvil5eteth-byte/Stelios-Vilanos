# One-post Metricool publisher

`publisher.py` completes the scheduling adapter after the existing exact-file
release preflight. It can create one new scheduled video through the currently
connected Metricool tools and immediately read back the actual record. It does
not install an unattended runner, activate a policy, generate media, upload media,
or obtain credentials. Actual connected execution and deployment on a shared
authoritative executor have not been tested or activated.

The current `PLATFORM_SPECIFIC_FIFTEEN_DAILY` policy allows at most **15 published
plus active pending videos per platform per Athens day**, 60 distinct stories in
total. Both the release preflight and fresh live-read cap use the same cadence
constant. Legacy journal entries and historical publications still count; changing
the program label never authorizes a duplicate.

## Exact transport and source evidence

`MetricoolConnectorTransport` calls only these currently exposed tool bindings:

| Operation | Exact tool | Arguments |
|---|---|---|
| Create once | `mcp__codex_apps__metricool_createscheduledpost` | `blogId`, `date`, serialized `info` |
| Read planner | `mcp__codex_apps__metricool_getscheduledposts` | `brandId`, `fromDate`, `toDate`, `timezone`, `extendedRange=false` |

The public video is already staged on `static.metricool.com`. Its URL goes into
`info.media`. It is not passed as a local upload in `mediaFiles`.
`info.publicationDate` always includes both `dateTime` and `Europe/Athens`;
the outer `date` is the same local timestamp. Only the selected provider's
`*Data` object is emitted. No prior post ID/UUID is submitted for a new create.

The scheduler body is corroborated by the primary implementation's
[`_build_post_info` and create implementation](https://github.com/vicampuzano/metricool-mcp/blob/ae34c22e5411b65e0ecf44f0d86788fb9f21a246/server.py)
and [`_build_post_request`](https://github.com/vicampuzano/metricool-mcp/blob/ae34c22e5411b65e0ecf44f0d86788fb9f21a246/client.py).
That public server exposes a newer flat snake-case tool interface; this module
uses the actual connected tool envelope above, not that alternative interface.
The field names `isAiGenerated`, `isAigc`, `isAiGeneratedContent`, YouTube
`type=short`, provider status, ID/UUID and publication-date readback were also
observed in 40 real October 9 records read from brand 7076410 on October 10.
Those private records are not included in this change.

There is no direct REST transport. Metricool's
[official API guide](https://help.metricool.com/basic-guide-for-api-integration-r97af)
documents different authentication and media requirements, so it must not be
treated as interchangeable with this connected tool contract.

## Integration host

The existing authorized host supplies a synchronous callable
`call_tool(tool_name, arguments)` that invokes its connected Metricool service
and returns the real MCP result. It must execute each call once, without implicit
transport retries. An asynchronous host must provide an appropriate synchronous
bridge; passing an unawaited coroutine is not a valid result.

The host also supplies `refresh()`. On **every attempt**, inside the delivery
lock, it must read the current canonical policy and complete Metricool, Notion,
repository/history and production-lease evidence. The returned object contains
`policy` and `history` for the existing `pipeline.release_preflight` contract.
It must not restamp a cached archive. The overall `history.checked_at` must be
at or after the start of this particular refresh call. Source errors, incomplete
history, missing semantic clearance, disabled flags, unowned/expired leases and
full daily capacity still block.

Every source receipt also needs its own timezone-aware `checked_at` and
`expires_at`, measured during this refresh and no more than five minutes old.
The three archive sources need `pagination_exhausted=true`; nested or snake-case
pagination markers that indicate remaining pages are rejected. Each source's
`observed_delivery_keys` records the journal idempotency keys independently found
in that source. A previous attempted delivery must be reconciled across Metricool,
Notion and the repository before another create. Current-day queue counts must
be refreshed during this invocation and account for successful journal entries.
Expiry is checked again after the media read, immediately before the durable claim.

For each successful journal entry scheduled on the current local date,
`history.queue_snapshot.platforms[platform].observed_delivery_keys` must contain
its idempotency key, attesting that the platform's `published + active_pending`
count includes that delivery. The count cannot be smaller than the number of
acknowledged successful journal entries for that platform. These acknowledgments
must come from real reconciliation; they are not approval flags to copy from a
previous run. All three source key lists and the platform count are needed.

The host imports `schedule_once` and `MetricoolConnectorTransport` from this
module and supplies the real job, base directory, refresh callback, transport and
private journal path. The default `execute=False` returns `DRY_RUN_NOT_SENT` and
performs no transport call or journal write. Only an explicitly authorized
integration may pass `execute=True`; that does not override any gate.

## Exact media prerequisites

The existing job's `final` record and actual review files remain mandatory.
No field in this module substitutes for actual listening, complete visual
inspection, subtitle synchronization or a valid exact SHA-bound review.

`job.delivery` additionally supplies:

| Field | Meaning |
|---|---|
| `media_url` | Already-staged HTTPS MP4 on `static.metricool.com` |
| `media_sha256` | Same SHA256 as the reviewed local final MP4 |
| `media_bytes` | Positive exact byte count |
| `youtube_made_for_kids` | Explicit boolean, required for YouTube |

The adapter reads the staged bytes and independently checks SHA256 and length
before creating. After the live write readback, it verifies the actual returned
media URL's bytes again. It does not normalize, transcode, upload to another host,
or substitute an asset. A mismatch blocks acceptance and never triggers retry.

Instagram Reels use `isAiGenerated=true`; TikTok videos use `isAigc=true` and
`autoAddMusic=false`; YouTube Shorts use `isAiGeneratedContent=true` with an
explicit audience. The actual returned native fields must match. TikTok can omit
the false photo-only `autoAddMusic` field in a video response, but a returned true
value is rejected.

**Facebook is blocked with `FACEBOOK_NATIVE_AI_FIELD_NOT_VERIFIED`.** The
documented/observed Metricool Facebook schema has no native AI toggle. The
standing automatic release rule still requires native disclosure. This module
does not invent a field or treat caption disclosure as an automatic waiver.
The observed Facebook payload builder is retained for schema inspection, but
the release path cannot use it until there is verified native-field support and
an appropriate reviewed code change.

Metricool's [official AI-labeling guide](https://help.metricool.com/how-to-label-ai-generated-content-for-eu-ai-act-compliance-8a1j8)
confirms the available native switches for Instagram, TikTok and YouTube and
the absence of a native Facebook switch in Metricool.

## One authoritative journal and exclusive lease

Use one private durable SQLite journal and the same authoritative external
production lease for all executors. A per-session scratch database is not an
operational deployment. Independent copies of a journal do not provide global
deduplication. The same path string on two hosts does not prove shared storage.
The deployment must verify its real storage durability and file-lock semantics;
this is not established by setting JSON flags.

In addition to the existing owned lease and authorized `release` action,
`history.sources.production_lease.delivery_executor_binding` must contain:

- `private=true` and `verified_shared_durable_store=true`, reflecting actual
  deployment evidence.
- `executor_id` matching the lease owner.
- `journal_path` matching the supplied absolute, resolved journal path.
- A real reviewer and SHA256 `evidence_sha256` of the deployment evidence.
- Fresh timezone-aware `checked_at`/`expires_at`, no older than five minutes.

No valid operational binding or operational QA receipt is supplied in this
change. Test fixtures are explicitly labelled and are not approvals.

The adapter holds the journal's nonblocking exclusive lock across refresh,
preflight, live queue read, create and readback. A competing executor fails closed.
SQLite uses full synchronous commits. The attempt is committed **before** the
non-idempotent create. Uniqueness covers its idempotency key, story ID, final
media hash, normalized fingerprint and normalized script hash. The receipt also
records the exact script hash. A timeout, crash, ambiguous reply or readback
failure leaves the attempt occupied and blocks all later creates until
reconciled. Changing a date, story ID, spacing or rendering does not silently
authorize reuse of a known fingerprint or script. An incompatible older journal
schema fails closed; it is never silently reset or supplied with empty identities.

Global duplicate prevention additionally depends on the freshly read complete
historical sources and the authoritative external lease. The local journal
alone does not discover work performed by another uncoordinated session.

## Results and recovery

Immediately after every attempted write, including exceptions, the adapter makes
one live planner read. It correlates by returned ID/UUID, or by the unique exact
media/text/date match if no identifiers returned. It verifies brand scope,
explicit brand fields when present, date/timezone, selected provider, ID, UUID,
media, caption, draft/autoPublish and native platform fields.

| State | Meaning |
|---|---|
| `SCHEDULED_PENDING` | Matching live record is PENDING; not published |
| `PUBLISHED` | Matching live provider explicitly reports PUBLISHED with its ID and public URL |
| `FAILED_NO_RETRY` | Matching live provider reports ERROR/FAILED |
| `UNKNOWN_REQUIRES_RECONCILIATION` | No complete trustworthy result; do not create another |

Successful readbacks are written to the private journal with IDs/UUID, provider
status, date/time, returned media and exact-byte verification. Fixed blocker codes
are preserved without arbitrary response bodies, credentials or exception URLs.
The caller must reconcile Notion and repository delivery history from this
receipt before the next job's fresh clearance. No separate write is disguised
as part of Metricool scheduling.

There is no reset/delete/retry function. Reconciliation of an uncertain or failed
attempt requires live provider evidence and a deliberate separate decision.
Absence from a planner response is not proof that nothing was published.

## Verification and limits

Run `python -m unittest discover -s tests -v` from `production/platform_specific`.
Tests exercise the actual connected-tool envelope and realistic MCP response
shape with mocked transport, along with policy/history/lease/audio failures,
newly consumed capacity, duplicate races, hash mismatches, timeout after success,
unknown writes, permanent no-retry state, native-field mismatch, brand mismatch
and the PENDING/PUBLISHED distinction. No real provider call or credential is
used. Saved real read response envelopes were also parsed locally without
including their contents in the repository.

This is implemented and locally tested adapter code. Actual connected create,
cross-host durable deployment and an unattended production runner remain
unvalidated/unactivated. Missing original content, exact final review, verified
zero-cost narration capacity and unsupported native disclosure remain separate
operational blockers. All existing production flags remain false.
