import concurrent.futures
import copy
import datetime as dt
import json
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pipeline as p
from synthesize_guarded import BudgetLedger, synthesize_job, validate_credentials
from render_local import FONT, parse_cues, render, wrap
from PIL import ImageFont

NOW = dt.datetime(2026, 10, 8, 20, 0, tzinfo=p.UTC)


def job(identifier="2026-10-09-youtube-01"):
    item = p.scaffold("2026-10-09")["jobs"][-10]
    item.update(id=identifier, story_id=identifier + "-story", title="Ένα μοναδικό τεστ", fingerprint=identifier + "-identity",
                script="Μια διαφορετική ιστορία δοκιμής με καθαρή αρχή και τέλος. " + p.CTA,
                caption="Πρωτότυπη μυθοπλασία. " + p.CTA, sources=[], kind="fiction")
    item["source_review"] = {"passed": True, "reviewer": "UNIT_TEST_FIXTURE", "story_sha256": p.story_hash(item)}
    item["tts_charge_upper_bound"] = len(item["script"]) + 100
    return item


def policy(enabled=True):
    return {"program_label": p.PROGRAM, "enabled": enabled,
            "active_schedule": enabled, "scheduling": {"enabled": enabled},
            "routing": {"active_publish_providers": list(p.PLATFORMS) if enabled else []},
            "production": {"enabled": enabled, "new_media_enabled": enabled, "publication_enabled": enabled, "scheduling_enabled": enabled},
            "platforms": {platform: {"enabled": enabled} for platform in p.PLATFORMS}}


def history(item, ledger_path=None):
    result = {"checked_at": (NOW - dt.timedelta(minutes=1)).isoformat(), "expires_at": (NOW + dt.timedelta(minutes=10)).isoformat(),
            "complete": True,
            "sources": {name: {"status": "READ_SUCCEEDED", "complete": True, "rows_seen": 1, "conflicting_active_lease": False} for name in p.HISTORY_SOURCES},
            "stories": [{"story_id": "an-unrelated-previous-story", "fingerprint": "different-concrete-story", "status": "PUBLISHED"}],
            "semantic_reviews": {item["id"]: {"clear": True, "reviewer": "UNIT_TEST_FIXTURE", "checked_at": NOW.isoformat(), "story_sha256": p.story_hash(item)}},
            "queue_snapshot": {"status": "READ_SUCCEEDED", "complete": True, "checked_at": NOW.isoformat(),
                               "expires_at": (NOW + dt.timedelta(minutes=5)).isoformat(), "brand_id": 7076410,
                               "timezone": "Europe/Athens", "local_date": "2026-10-09",
                               "platforms": {platform: {"published": 0, "active_pending": 0} for platform in p.PLATFORMS}}}
    result["sources"]["production_lease"].update(owned_active_lease=True, owner="UNIT_TEST_FIXTURE", brand_id=7076410,
                                               local_date="2026-10-09", authorized_actions=["synthesize", "render", "release"],
                                               lease_expires_at=(NOW + dt.timedelta(minutes=15)).isoformat())
    if ledger_path is not None:
        result["sources"]["production_lease"]["executor_binding"] = {
            "private": True, "verified_shared_durable_store": True, "executor_id": "UNIT_TEST_FIXTURE",
            "ledger_path": str(ledger_path.resolve()), "resource_id": budget()["resource_id"], "period": "2026-10",
            "reviewer": "UNIT_TEST_FIXTURE", "evidence_sha256": "c" * 64,
            "checked_at": NOW.isoformat(), "expires_at": (NOW + dt.timedelta(minutes=10)).isoformat()}
    return result


def budget(remaining=100000):
    result = {"checked_at": NOW.isoformat(), "expires_at": (NOW + dt.timedelta(minutes=10)).isoformat(), "complete": True,
            "resource_id": "/subscriptions/UNIT-TEST/resourceGroups/UNIT-TEST/providers/Microsoft.CognitiveServices/accounts/UNIT-TEST",
            "actual_sku": "F0", "zero_cost_verified": True, "usage_complete_for_period": True,
            "reviewer": "UNIT_TEST_FIXTURE", "source": "azure_management_live_read", "evidence_sha256": "a" * 64,
            "period": "2026-10", "voice": p.VOICE, "remaining_tts_characters": remaining}
    result["credential_binding"] = {"private": True, "verified_same_resource": True, "resource_id": result["resource_id"],
                                    "region": "unittest", "endpoint": "https://unittest.tts.speech.microsoft.com",
                                    "key_sha256": hashlib.sha256(b"UNIT_TEST_NO_REAL_KEY").hexdigest()}
    return result


def media_probe(duration="90.0"):
    return {"format": {"duration": duration}, "streams": [
        {"codec_type": "video", "codec_name": "h264", "width": 1080, "height": 1920, "pix_fmt": "yuv420p", "r_frame_rate": "30/1"},
        {"codec_type": "audio", "codec_name": "aac", "sample_rate": "48000", "channels": 1}]}


def final_fixture(item, directory):
    media = directory / "fixture.bin"
    media.write_bytes(b"NOT A REAL VIDEO: only the hash-binding unit test fixture")
    binding = {"job_id": item["id"], "platform": item["platform"], "story_sha256": p.story_hash(item), "media_sha256": p.sha256(media)}
    technical = {**binding, "created_at": (NOW - dt.timedelta(hours=1)).isoformat(), "full_decode_passed": True,
                 "technical_passed": True, "subtitle_text_verified": True, "duration_seconds": 90.0,
                 "width": 1080, "height": 1920, "fps": 30, "video_codec": "h264", "pixel_format": "yuv420p",
                 "audio_codec": "aac", "audio_rate": 48000, "audio_channels": 1, "voice": p.VOICE,
                 "background_music": False, "avatar": False, "audio_stretched": False, "audio_padded": False}
    review = {**binding, "reviewer": "UNIT_TEST_FIXTURE", "reviewed_at": NOW.isoformat(), "actual_audio_listened": True,
              "complete_audio_review_passed": True, "nestoras_voice_confirmed": True, "visual_review_passed": True,
              "all_scenes_reviewed": True, "all_subtitle_cues_reviewed": True, "pronunciation_passed": True,
              "subtitle_sync_passed": True, "opening_reviewed": True, "complete_cta_reviewed": True, "passed_final_review": True}
    p.write_json(directory / "technical.json", technical)
    p.write_json(directory / "review.json", review)
    item["final"] = {"path": str(media), "sha256": p.sha256(media), "technical_path": str(directory / "technical.json"),
                     "technical_sha256": p.sha256(directory / "technical.json"), "review_path": str(directory / "review.json"),
                     "review_sha256": p.sha256(directory / "review.json")}
    return technical, review


class ManifestTests(unittest.TestCase):
    def test_exact_40_not_10_shared(self):
        manifest = p.scaffold("2026-10-09")
        self.assertEqual(p.validate_manifest(manifest), [])
        manifest["jobs"] = manifest["jobs"][:10]
        self.assertTrue(p.validate_manifest(manifest))

    def test_duplicate_body_across_platforms(self):
        manifest = p.scaffold("2026-10-09")
        first, second = manifest["jobs"][0], manifest["jobs"][10]
        first.update(story_id="one", title="first", fingerprint="one", script="Ίδιο κείμενο. " + p.CTA)
        second.update(story_id="two", title="renamed", fingerprint="two", script="Ίδιο κείμενο. " + p.CTA)
        self.assertTrue(any("duplicate script" in error for error in p.validate_manifest(manifest)))

    def test_multiple_platforms_rejected(self):
        manifest = p.scaffold("2026-10-09")
        manifest["jobs"][0]["platform"] = ["facebook", "instagram"]
        self.assertIn("one platform string", p.validate_manifest(manifest)[0])

    def test_empty_slots_never_count_as_queue(self):
        result = p.plan(p.scaffold("2026-10-09"), Path("."), policy(False), {}, {}, NOW)
        self.assertEqual(result["real_scheduled_queue_count"], 0)
        self.assertEqual(sum(platform["source_packs"] for platform in result["per_platform"].values()), 0)
        self.assertFalse(result["daily_complete"])

    def test_catalog_import_preserves_one_platform_and_no_pass(self):
        source = job()
        manifest = p.import_catalog(p.scaffold("2026-10-09"), [source])
        assigned = next(item for item in manifest["jobs"] if item.get("story_id"))
        self.assertEqual(assigned["platform"], "youtube")
        self.assertNotIn("source_review", assigned)
        self.assertEqual(assigned["stage"], "SOURCE_PACK_IMPORTED_NOT_REVIEWED")

    def test_catalog_date_alias_does_not_silently_move_story(self):
        source = job()
        source.pop("local_date")
        source["date"] = "2026-10-10"
        manifest = p.import_catalog(p.scaffold("2026-10-09"), [source])
        self.assertFalse(any(item.get("story_id") for item in manifest["jobs"]))


class HistoryAndBudgetTests(unittest.TestCase):
    def test_unverified_receipt_templates_with_null_timestamps_fail_closed(self):
        item = job()
        receipt = {"checked_at": None, "expires_at": None, "complete": False}
        self.assertIn("FRESH_HISTORY_REQUIRED", p.history_errors(item, receipt, NOW))
        self.assertIn("FRESH_ACCOUNT_BUDGET_REQUIRED", p.budget_errors(item, receipt, NOW))

    def test_hidden_error_overrides_outer_success(self):
        item = job()
        receipt = history(item)
        receipt["sources"]["notion"]["error_code"] = "usage_limit_reached"
        self.assertTrue(p.history_errors(item, receipt, NOW))

    def test_empty_archive_is_not_clearance(self):
        item = job()
        receipt = history(item)
        receipt["stories"] = []
        self.assertIn("EMPTY_HISTORY_IS_NOT_CLEARANCE", p.history_errors(item, receipt, NOW))

    def test_modified_script_invalidates_semantic_review(self):
        item = job()
        receipt = history(item)
        item["script"] = "Νέα αρχή. " + item["script"]
        self.assertIn("SEMANTIC_DUPLICATE_REVIEW_REQUIRED", p.history_errors(item, receipt, NOW))

    def test_published_exact_story_blocked(self):
        item = job()
        receipt = history(item)
        receipt["stories"].append({"story_id": item["story_id"], "status": "PUBLISHED"})
        self.assertIn("DUPLICATE_IN_LIVE_HISTORY", p.history_errors(item, receipt, NOW))

    def test_unknown_or_stale_or_paid_account_blocks(self):
        item = job()
        for change in ({"actual_sku": "S0"}, {"remaining_tts_characters": None}, {"complete": False},
                       {"checked_at": (NOW - dt.timedelta(hours=1)).isoformat()}):
            receipt = budget()
            receipt.update(change)
            self.assertTrue(p.budget_errors(item, receipt, NOW), change)

    def test_current_disabled_policy_makes_zero_provider_calls(self):
        item, provider = job(), mock.Mock(side_effect=AssertionError("Provider must not run"))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(p.Blocked):
                synthesize_job(item, policy(False), history(item), budget(), root / "ledger.json", root / "audio", execute=True, provider=provider, now=NOW)
            provider.assert_not_called()
            self.assertFalse((root / "audio").exists())
            self.assertFalse((root / "ledger.json").exists())

    def test_unknown_budget_makes_zero_provider_calls_even_enabled(self):
        item, provider = job(), mock.Mock()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(p.Blocked):
                synthesize_job(item, policy(), history(item), {}, root / "ledger.json", root / "audio", execute=True, provider=provider, now=NOW)
            provider.assert_not_called()

    def test_atomic_reservations_prevent_double_spend(self):
        a, b = job("a"), job("b")
        receipt = budget(a["tts_charge_upper_bound"])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.json"
            def reserve(item):
                try:
                    BudgetLedger(path).reserve(item, receipt, NOW)
                    return True
                except p.Blocked:
                    return False
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(reserve, (a, b)))
            self.assertEqual(sum(results), 1)
            self.assertEqual(len(p.read_json(path)["attempts"]), 1)

    def test_unknown_attempt_is_retained_and_never_retried(self):
        item = job()
        with tempfile.TemporaryDirectory() as tmp:
            ledger = BudgetLedger(Path(tmp) / "ledger.json")
            identifier = ledger.reserve(item, budget(), NOW)
            ledger.finish(identifier, "UNKNOWN")
            with self.assertRaisesRegex(p.Blocked, "never auto-retry"):
                ledger.reserve(item, budget(), NOW)

    def test_provider_failure_marks_unknown_with_one_call(self):
        item, provider = job(), mock.Mock(side_effect=RuntimeError("simulated transport failure"))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with mock.patch.dict("os.environ", {"AZURE_SPEECH_KEY": "UNIT_TEST_NO_REAL_KEY", "AZURE_SPEECH_REGION": "unittest"}), self.assertRaises(RuntimeError):
                synthesize_job(item, policy(), history(item, root / "ledger.json"), budget(), root / "ledger.json", root / "audio", execute=True, provider=provider, now=NOW)
            self.assertEqual(provider.call_count, 1)
            self.assertEqual(p.read_json(root / "ledger.json")["attempts"][0]["status"], "UNKNOWN")

    def test_actual_key_or_region_mismatch_blocks_before_call(self):
        for environment in ({"AZURE_SPEECH_KEY": "WRONG_TEST_KEY", "AZURE_SPEECH_REGION": "unittest"},
                            {"AZURE_SPEECH_KEY": "UNIT_TEST_NO_REAL_KEY", "AZURE_SPEECH_REGION": "wrongregion"}):
            provider, item = mock.Mock(), job()
            with tempfile.TemporaryDirectory() as tmp, mock.patch.dict("os.environ", environment):
                root = Path(tmp)
                with self.assertRaisesRegex(p.Blocked, "binding"):
                    synthesize_job(item, policy(), history(item), budget(), root / "ledger.json", root / "audio", execute=True, provider=provider, now=NOW)
                provider.assert_not_called()
                self.assertFalse((root / "ledger.json").exists())

    def test_unbound_or_mismatched_executor_ledger_blocks_before_call(self):
        item = job()
        changes = (None, {"ledger_path": "/private/another-worker-ledger.json"},
                   {"resource_id": "a-different-resource"}, {"period": "2026-11"},
                   {"executor_id": "a-different-executor"}, {"verified_shared_durable_store": False})
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict("os.environ", {
                "AZURE_SPEECH_KEY": "UNIT_TEST_NO_REAL_KEY", "AZURE_SPEECH_REGION": "unittest"}):
            root = Path(tmp)
            for change in changes:
                with self.subTest(change=change):
                    receipt, provider = history(item, root / "ledger.json"), mock.Mock()
                    lease = receipt["sources"]["production_lease"]
                    if change is None:
                        lease.pop("executor_binding")
                    else:
                        lease["executor_binding"].update(change)
                    with self.assertRaisesRegex(p.Blocked, "EXECUTOR_LEDGER_BINDING"):
                        synthesize_job(item, policy(), receipt, budget(), root / "ledger.json", root / "audio",
                                       execute=True, provider=provider, now=NOW)
                    provider.assert_not_called()
                    self.assertFalse((root / "ledger.json").exists())
                    self.assertFalse((root / "audio").exists())

    def test_newer_receipt_does_not_erase_consumed_reservation(self):
        first, second = job("first"), job("second")
        allowance = first["tts_charge_upper_bound"]
        with tempfile.TemporaryDirectory() as tmp:
            ledger = BudgetLedger(Path(tmp) / "ledger.json")
            identifier = ledger.reserve(first, budget(allowance), NOW)
            ledger.finish(identifier, "CONSUMED", "b" * 64)
            newer = budget(allowance)
            newer["checked_at"] = (NOW + dt.timedelta(minutes=1)).isoformat()
            newer["expires_at"] = (NOW + dt.timedelta(minutes=11)).isoformat()
            with self.assertRaisesRegex(p.Blocked, "INSUFFICIENT"):
                ledger.reserve(second, newer, NOW + dt.timedelta(minutes=1))

    def test_unknown_reservation_cannot_be_released_by_included_ids(self):
        first, second = job("first"), job("second")
        with tempfile.TemporaryDirectory() as tmp:
            ledger = BudgetLedger(Path(tmp) / "ledger.json")
            identifier = ledger.reserve(first, budget(first["tts_charge_upper_bound"]), NOW)
            ledger.finish(identifier, "UNKNOWN")
            receipt = budget(first["tts_charge_upper_bound"])
            receipt.update(included_attempt_ids=[identifier], usage_window_end=NOW.isoformat())
            with self.assertRaisesRegex(p.Blocked, "INSUFFICIENT"):
                ledger.reserve(second, receipt, NOW)

    def test_prepare_only_lease_cannot_authorize_provider_call(self):
        item, receipt, provider = job(), history(job()), mock.Mock()
        receipt["sources"]["production_lease"]["authorized_actions"] = ["prepare"]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaisesRegex(p.Blocked, "OWNED_ACTIVE_LEASE"):
                synthesize_job(item, policy(), receipt, budget(), root / "ledger.json", root / "audio", execute=True, provider=provider, now=NOW)
            provider.assert_not_called()

    def test_out_of_range_duration_consumes_once_and_does_not_retry(self):
        item = job()
        wav = b"RIFF" + b"UNIT_TEST_AUDIO_BYTES" * 100
        provider = mock.Mock(return_value=(wav, []))
        def fake_trim(arguments):
            Path(arguments[-1]).write_bytes(wav)
            return ""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with mock.patch.dict("os.environ", {"AZURE_SPEECH_KEY": "UNIT_TEST_NO_REAL_KEY", "AZURE_SPEECH_REGION": "unittest"}), \
                    mock.patch("render_local.run", side_effect=fake_trim), \
                    mock.patch("render_local.probe", return_value={"format": {"duration": "79.5"}}), \
                    self.assertRaisesRegex(p.Blocked, "outside 80"):
                synthesize_job(item, policy(), history(item, root / "ledger.json"), budget(), root / "ledger.json", root / "audio", execute=True, provider=provider, now=NOW)
            self.assertEqual(provider.call_count, 1)
            attempt = p.read_json(root / "ledger.json")["attempts"][0]
            self.assertEqual(attempt["status"], "CONSUMED")
            self.assertEqual(attempt["audio_sha256"], p.sha256(root / "audio/nestoras.wav"))
            self.assertFalse((root / "audio/audio.json").exists())

    def test_plan_cumulative_budget(self):
        manifest = p.scaffold("2026-10-09")
        source_a, source_b = job("a"), job("b")
        source_b.update(title="Δεύτερη δοκιμή", script="Μία άλλη ιστορία. " + p.CTA)
        manifest["jobs"][-10] = source_a
        source_b["slot_local"] = "09:00"
        manifest["jobs"][-9] = source_b
        result = p.plan(manifest, Path("."), policy(), {}, budget(source_a["tts_charge_upper_bound"]), NOW)
        self.assertFalse(result["manifest_errors"])
        self.assertIn("INSUFFICIENT_FREE_TTS_CAPACITY", result["jobs"][-9]["blockers"])


class FinalAndReleaseTests(unittest.TestCase):
    def test_future_review_or_render_timestamp_cannot_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, item = Path(tmp), job()
            for field in ("reviewed_at", "created_at"):
                with self.subTest(field=field):
                    technical, review = final_fixture(item, root)
                    record = review if field == "reviewed_at" else technical
                    record[field] = (NOW + dt.timedelta(minutes=1)).isoformat()
                    p.write_json(root / "technical.json", technical)
                    p.write_json(root / "review.json", review)
                    item["final"].update(technical_sha256=p.sha256(root / "technical.json"),
                                         review_sha256=p.sha256(root / "review.json"))
                    with mock.patch("pipeline.probe_media", return_value=media_probe()):
                        self.assertIn("FINAL_EVIDENCE_TIMESTAMP_IN_FUTURE", p.final_errors(item, root, NOW))

    def test_byte_change_invalidates_passed_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, item = Path(tmp), job()
            final_fixture(item, root)
            Path(item["final"]["path"]).write_bytes(b"CHANGED")
            self.assertTrue(p.final_errors(item, root))

    def test_false_audio_review_cannot_be_passed_by_visual(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, item = Path(tmp), job()
            _, review = final_fixture(item, root)
            review["actual_audio_listened"] = False
            p.write_json(root / "review.json", review)
            item["final"]["review_sha256"] = p.sha256(root / "review.json")
            with mock.patch("pipeline.probe_media", return_value=media_probe()):
                self.assertIn("ACTUAL_EXACT_FINAL_AUDIO_AND_VISUAL_REVIEW_REQUIRED", p.final_errors(item, root))

    def test_technical_pass_label_does_not_override_bad_duration(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, item = Path(tmp), job()
            technical, _ = final_fixture(item, root)
            technical["duration_seconds"] = 20
            p.write_json(root / "technical.json", technical)
            item["final"]["technical_sha256"] = p.sha256(root / "technical.json")
            self.assertIn("FINAL_TECHNICAL_FORMAT_MISMATCH", p.final_errors(item, root))

    def test_actual_probe_overrides_forged_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, item = Path(tmp), job()
            final_fixture(item, root)
            with mock.patch("pipeline.probe_media", return_value=media_probe("20")):
                self.assertIn("EXACT_FINAL_PROBE_MISMATCH", p.final_errors(item, root))
            # Real ffprobe also rejects our deliberately non-media test bytes.
            self.assertIn("EXACT_FINAL_PROBE_FAILED", p.final_errors(item, root))

    def test_existing_published_plus_pending_enforces_cap(self):
        item, receipt = job(), history(job())
        receipt["queue_snapshot"]["platforms"]["youtube"] = {"published": 6, "active_pending": 4}
        self.assertIn("DAILY_PLATFORM_CAP_REACHED", p.queue_capacity_errors(item, receipt, NOW))
        receipt["queue_snapshot"]["platforms"]["youtube"]["active_pending"] = 3
        self.assertEqual(p.queue_capacity_errors(item, receipt, NOW), [])

    def test_other_day_or_brand_count_cannot_clear_queue(self):
        item = job()
        for field, value in (("brand_id", 1), ("local_date", "2026-10-08"), ("complete", False)):
            receipt = history(item)
            receipt["queue_snapshot"][field] = value
            self.assertTrue(p.queue_capacity_errors(item, receipt, NOW))

    def test_release_handoff_is_not_published_and_requires_live_readback(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, item = Path(tmp), job()
            final_fixture(item, root)
            item["native_ai_disclosure"] = {"platform": "youtube", "verified": True, "evidence": "UNIT_TEST_FIXTURE"}
            with mock.patch("pipeline.probe_media", return_value=media_probe()):
                handoff = p.release_preflight(item, root, policy(), history(item), NOW)
            self.assertEqual(handoff["status"], "RELEASE_HANDOFF_ONLY_NOT_SCHEDULED")
            self.assertTrue(handoff["requires_live_write_readback"])

    def assert_release_policy_blocked(self, candidate, expected):
        # These local UNIT_TEST_FIXTURE records are never operational evidence.
        # All existing source/history/lease/final gates run; only ffprobe of the
        # deliberately fake bytes is mocked to isolate the routing regression.
        with tempfile.TemporaryDirectory() as tmp:
            root, item = Path(tmp), job()
            final_fixture(item, root)
            item["native_ai_disclosure"] = {"platform": "youtube", "verified": True, "evidence": "UNIT_TEST_FIXTURE"}
            with mock.patch("pipeline.probe_media", return_value=media_probe()):
                with self.assertRaisesRegex(p.Blocked, expected):
                    p.release_preflight(item, root, candidate, history(item), NOW)

    def test_release_requires_both_schedule_flags(self):
        for field in ("active_schedule", "scheduling"):
            candidate = policy()
            candidate[field] = False if field == "active_schedule" else {"enabled": False}
            with self.subTest(field=field):
                self.assert_release_policy_blocked(candidate, "ACTIVE_SCHEDULE_DISABLED")

    def test_release_missing_schedule_flags_fail_closed(self):
        for field in ("active_schedule", "scheduling"):
            candidate = policy()
            del candidate[field]
            with self.subTest(field=field):
                self.assert_release_policy_blocked(candidate, "ACTIVE_SCHEDULE_DISABLED")

    def test_connected_inventory_does_not_authorize_a_target(self):
        for allowed in ([], ["facebook", "instagram", "tiktok"]):
            candidate = policy()
            candidate["routing"] = {"connected_network_inventory": list(p.PLATFORMS),
                                    "active_publish_providers": allowed}
            with self.subTest(allowed=allowed):
                self.assert_release_policy_blocked(candidate, "PLATFORM_NOT_IN_PUBLISH_ALLOWLIST")

    def test_missing_or_malformed_publish_allowlist_fails_closed(self):
        for allowed in (None, "youtube", ["youtube", "youtube"], ["youtube", "unknown"], [{"network": "youtube"}]):
            candidate = policy()
            candidate["routing"]["active_publish_providers"] = allowed
            with self.subTest(allowed=allowed):
                self.assert_release_policy_blocked(candidate, "PUBLISH_PROVIDER_ALLOWLIST_INVALID")
        candidate = policy()
        del candidate["routing"]
        self.assert_release_policy_blocked(candidate, "PUBLISH_PROVIDER_ALLOWLIST_INVALID")


class LocalMediaTests(unittest.TestCase):
    def test_subtitle_word_loss_rejected(self):
        script = "Μια δοκιμή. " + p.CTA
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "subs.srt"
            path.write_text("1\n00:00:00,000 --> 00:01:27,000\nΜια δοκιμή.\n\n2\n00:01:27,000 --> 00:01:30,000\n" + p.CTA, encoding="utf-8")
            self.assertEqual(parse_cues(path, 90, script)[-1]["text"], p.CTA)
            with self.assertRaisesRegex(p.Blocked, "word sequence"):
                parse_cues(path, 90, "Λείπει μια λέξη. " + script)

    def test_measured_greek_subtitle_overflow_rejected(self):
        font = ImageFont.truetype(str(FONT), 52)
        lines = wrap("Αν σας άρεσε, ακολουθήστε για περισσότερα.", font)
        self.assertLessEqual(len(lines), 2)
        self.assertTrue(all(font.getlength(line) <= 816 for line in lines))
        with self.assertRaises(p.Blocked):
            wrap("Μεγαλύτερη " * 30, font)

    def test_disabled_policy_prevents_local_render_before_ffmpeg(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch("render_local.probe") as probe:
            with self.assertRaises(p.Blocked):
                render(job(), Path(tmp), Path(tmp) / "output", policy(False), {})
            probe.assert_not_called()
            self.assertFalse((Path(tmp) / "output").exists())


if __name__ == "__main__":
    unittest.main()
