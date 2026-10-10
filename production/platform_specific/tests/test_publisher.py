"""Failure-focused tests; all credentials/media/receipts are unit-test fixtures."""
import copy
import datetime as dt
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest import mock

import pipeline as p
import publisher as pub
from test_pipeline import NOW, job, policy, history, final_fixture, media_probe


class FakeConnector:
    def __init__(self, item):
        self.item = item
        self.rows = []
        self.calls = []
        self.mode = "normal"
        self.mutate = None
        self.reads = 0

    def __call__(self, name, arguments):
        self.calls.append((name, copy.deepcopy(arguments)))
        if name == pub.READ_TOOL:
            self.reads += 1
            if self.mode == "bad_readback" and self.reads > 1:
                return {"isError": True, "content": [{"type": "text", "text": "fixture error"}]}
            return {"content": [{"type": "text", "text": json.dumps({"data": self.rows})}], "isError": False}
        if name != pub.CREATE_TOOL:
            raise AssertionError("Unexpected tool")
        if self.mode == "timeout_before_result":
            raise TimeoutError("UNIT_TEST_FIXTURE")
        row = json.loads(arguments["info"])
        row.update(id=123, uuid="UNIT_TEST_UUID")
        row["providers"][0].update(status="PENDING")
        if self.mode == "published":
            row["providers"][0].update(status="PUBLISHED", id="UNIT_TEST_PROVIDER_ID", publicUrl="https://www.youtube.com/shorts/UNIT_TEST")
        if self.mode == "provider_failed":
            row["providers"][0].update(status="ERROR")
        if self.mutate:
            self.mutate(row)
        self.rows.append(row)
        if self.mode == "timeout_after_accept":
            raise TimeoutError("UNIT_TEST_FIXTURE")
        return {"data": {"id": 123, "uuid": "UNIT_TEST_UUID"}}

    def digest(self, url):
        return {"sha256": self.item["final"]["sha256"], "bytes": Path(self.item["final"]["path"]).stat().st_size}

    @property
    def creates(self):
        return sum(name == pub.CREATE_TOOL for name, _ in self.calls)


class PublisherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.journal = self.root / "durable_test_fixture.sqlite"
        self.item = job()
        final_fixture(self.item, self.root)
        self.item["native_ai_disclosure"] = {"platform": "youtube", "verified": True, "evidence": "UNIT_TEST_FIXTURE"}
        self.item["delivery"] = {"media_url": "https://static.metricool.com/planner/202610/UNIT_TEST.mp4",
            "media_sha256": self.item["final"]["sha256"],
            "media_bytes": Path(self.item["final"]["path"]).stat().st_size,
            "youtube_made_for_kids": False}
        self.current_policy = policy()
        self.current_history = history(self.item)
        self.current_history["checked_at"] = NOW.isoformat()
        for source in self.current_history["sources"].values():
            source.update(checked_at=NOW.isoformat(), expires_at=(NOW + dt.timedelta(minutes=4)).isoformat(),
                          pagination_exhausted=True, observed_delivery_keys=[])
        self.current_history["sources"]["production_lease"]["delivery_executor_binding"] = {
            "private": True, "verified_shared_durable_store": True, "executor_id": "UNIT_TEST_FIXTURE",
            "reviewer": "UNIT_TEST_FIXTURE", "evidence_sha256": "a" * 64,
            "journal_path": str(self.journal), "checked_at": NOW.isoformat(),
            "expires_at": (NOW + dt.timedelta(minutes=4)).isoformat()}
        self.fake = FakeConnector(self.item)
        self.transport = pub.MetricoolConnectorTransport(self.fake, self.fake.digest)
        self.refresh_calls = 0
        self.probe = mock.patch("pipeline.probe_media", return_value=media_probe())
        self.probe.start()

    def tearDown(self):
        self.probe.stop()
        self.temp.cleanup()

    def refresh(self):
        self.refresh_calls += 1
        return {"policy": self.current_policy, "history": self.current_history}

    def run_job(self, execute=True):
        return pub.schedule_once(self.item, self.root, self.refresh, self.transport, self.journal,
                                 execute=execute, clock=lambda: NOW)

    def test_exact_connector_envelope_and_immediate_live_readback(self):
        result = self.run_job()
        self.assertEqual(result["state"], "SCHEDULED_PENDING")
        self.assertEqual((result["metricool_id"], result["metricool_uuid"]), (123, "UNIT_TEST_UUID"))
        self.assertEqual([name for name, _ in self.fake.calls], [pub.READ_TOOL, pub.CREATE_TOOL, pub.READ_TOOL])
        args = self.fake.calls[1][1]
        self.assertEqual(set(args), {"blogId", "date", "info"})
        self.assertEqual(args["blogId"], "7076410")
        body = json.loads(args["info"])
        self.assertEqual(args["date"], body["publicationDate"]["dateTime"])
        self.assertEqual(body["publicationDate"]["timezone"], "Europe/Athens")
        self.assertEqual(body["providers"], [{"network": "youtube"}])
        self.assertEqual([k for k in body if k.endswith("Data")], ["youtubeData"])
        self.assertTrue(body["youtubeData"]["isAiGeneratedContent"])
        self.assertFalse(body["youtubeData"]["madeForKids"])

    def test_dry_run_never_calls_transport_or_creates_journal(self):
        result = self.run_job(execute=False)
        self.assertEqual(result["state"], "DRY_RUN_NOT_SENT")
        self.assertEqual(self.fake.calls, [])
        self.assertFalse(self.journal.exists())

    def test_disabled_policy_never_calls_connector(self):
        self.current_policy = policy(False)
        with self.assertRaises(p.Blocked):
            self.run_job()
        self.assertEqual(self.fake.calls, [])

    def test_cached_or_incomplete_history_cannot_release(self):
        self.current_history["checked_at"] = (NOW - dt.timedelta(seconds=1)).isoformat()
        with self.assertRaisesRegex(p.Blocked, "NEW_COMPLETE_HISTORY_READ"):
            self.run_job()
        self.current_history["checked_at"] = NOW.isoformat()
        self.current_history["sources"]["notion"]["complete"] = False
        with self.assertRaises(p.Blocked):
            self.run_job()
        self.assertEqual(self.fake.creates, 0)

    def test_missing_shared_journal_binding_blocks(self):
        del self.current_history["sources"]["production_lease"]["delivery_executor_binding"]
        with self.assertRaisesRegex(p.Blocked, "SHARED_DELIVERY_JOURNAL"):
            self.run_job()
        self.assertEqual(self.fake.calls, [])

    def test_actual_audio_review_still_required(self):
        path = Path(self.item["final"]["review_path"])
        review = json.loads(path.read_text())
        review["actual_audio_listened"] = False
        p.write_json(path, review)
        self.item["final"]["review_sha256"] = p.sha256(path)
        with self.assertRaisesRegex(p.Blocked, "ACTUAL_EXACT_FINAL_AUDIO"):
            self.run_job()
        self.assertEqual(self.fake.calls, [])

    def test_remote_bytes_mismatch_blocks_before_create(self):
        self.transport.media_digest = lambda _: {"sha256": "0" * 64, "bytes": 1}
        with self.assertRaisesRegex(p.Blocked, "EXACT_STAGED_BYTES"):
            self.run_job()
        self.assertEqual(self.fake.creates, 0)

    def test_new_pending_post_consumes_remaining_capacity(self):
        self.current_history["queue_snapshot"]["platforms"]["youtube"]["published"] = 9
        self.fake.rows = [{"id": 99, "text": "different", "media": ["different"],
            "publicationDate": {"dateTime": "2026-10-09T06:00:00", "timezone": pub.ZONE},
            "providers": [{"network": "youtube", "status": "PENDING"}], "draft": False, "autoPublish": True}]
        with self.assertRaisesRegex(p.Blocked, "DAILY_PLATFORM_CAP"):
            self.run_job()
        self.assertEqual(self.fake.creates, 0)

    def test_duplicate_in_new_live_read_blocks(self):
        self.fake.rows = [{"media": [self.item["delivery"]["media_url"]]}]
        with self.assertRaisesRegex(p.Blocked, "DUPLICATE_IN_FRESH"):
            self.run_job()
        self.assertEqual(self.fake.creates, 0)

    def test_timeout_after_accept_reconciles_without_retry(self):
        self.fake.mode = "timeout_after_accept"
        self.assertEqual(self.run_job()["state"], "SCHEDULED_PENDING")
        self.assertEqual(self.fake.creates, 1)

    def test_unknown_write_is_durable_and_never_retried(self):
        self.fake.mode = "timeout_before_result"
        self.assertEqual(self.run_job()["state"], "UNKNOWN_REQUIRES_RECONCILIATION")
        with self.assertRaisesRegex(p.Blocked, "ALREADY_ATTEMPTED_NO_RETRY"):
            self.run_job()
        self.assertEqual(self.fake.creates, 1)
        with sqlite3.connect(self.journal) as db:
            self.assertEqual(db.execute("SELECT state FROM attempts").fetchone()[0], "UNKNOWN_REQUIRES_RECONCILIATION")

    def test_successful_attempt_cannot_be_scheduled_again(self):
        self.run_job()
        with self.assertRaisesRegex(p.Blocked, "ALREADY_ATTEMPTED_NO_RETRY"):
            self.run_job()
        self.assertEqual(self.fake.creates, 1)

    def test_provider_failed_is_recorded_without_retry(self):
        self.fake.mode = "provider_failed"
        self.assertEqual(self.run_job()["state"], "FAILED_NO_RETRY")
        self.assertEqual(self.fake.creates, 1)

    def test_pending_is_never_reported_as_published(self):
        result = self.run_job()
        self.assertEqual(result["state"], "SCHEDULED_PENDING")
        self.assertFalse(result["published"])

    def test_published_requires_live_provider_id_and_url(self):
        self.fake.mode = "published"
        self.assertEqual(self.run_job()["state"], "PUBLISHED")

    def test_wrong_provider_or_native_label_fails_readback(self):
        self.fake.mutate = lambda row: row["youtubeData"].update(isAiGeneratedContent=False)
        self.assertEqual(self.run_job()["state"], "UNKNOWN_REQUIRES_RECONCILIATION")
        self.assertEqual(self.fake.creates, 1)

    def test_readback_error_never_retries_write(self):
        self.fake.mode = "bad_readback"
        self.assertEqual(self.run_job()["state"], "UNKNOWN_REQUIRES_RECONCILIATION")
        self.assertEqual(self.fake.creates, 1)

    def test_returned_explicit_wrong_brand_blocks(self):
        self.fake.mutate = lambda row: row.update(blogId=1)
        result = self.run_job()
        self.assertEqual(result["state"], "UNKNOWN_REQUIRES_RECONCILIATION")
        self.assertEqual(result["readback_error_code"], "LIVE_BRAND_MISMATCH")
        self.assertEqual(self.fake.creates, 1)

    def test_outer_fresh_timestamp_cannot_mask_stale_source(self):
        self.current_history["sources"]["notion"]["checked_at"] = (NOW - dt.timedelta(days=1)).isoformat()
        with self.assertRaisesRegex(p.Blocked, "NEW_SOURCE_READ_REQUIRED:notion"):
            self.run_job()
        self.assertEqual(self.fake.creates, 0)

    def test_source_expiry_during_media_read_blocks_before_durable_claim(self):
        self.current_history["sources"]["notion"]["expires_at"] = (NOW + dt.timedelta(minutes=1)).isoformat()
        current = [NOW]
        def slow_digest(url):
            current[0] = NOW + dt.timedelta(minutes=2)
            return self.fake.digest(url)
        self.transport.media_digest = slow_digest
        with self.assertRaisesRegex(p.Blocked, "NEW_SOURCE_READ_REQUIRED:notion"):
            pub.schedule_once(self.item, self.root, self.refresh, self.transport, self.journal,
                              execute=True, clock=lambda: current[0])
        self.assertEqual(self.fake.creates, 0)
        with sqlite3.connect(self.journal) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM attempts").fetchone()[0], 0)

    def test_recent_queue_from_before_current_refresh_is_not_clearance(self):
        self.current_history["queue_snapshot"]["checked_at"] = (NOW - dt.timedelta(seconds=1)).isoformat()
        with self.assertRaisesRegex(p.Blocked, "NEW_QUEUE_READ_REQUIRED_FOR_THIS_CREATE"):
            self.run_job()
        self.assertEqual(self.fake.creates, 0)

    def test_all_external_pages_must_be_exhausted(self):
        self.current_history["sources"]["repository"]["pagination_exhausted"] = False
        with self.assertRaises(p.Blocked):
            self.run_job()
        self.assertEqual(self.fake.creates, 0)

    def test_full_history_rehosted_identical_media_is_duplicate(self):
        self.current_history["stories"][0]["final_sha256"] = self.item["final"]["sha256"]
        with self.assertRaisesRegex(p.Blocked, "DUPLICATE_FINAL_MEDIA_IN_FULL_HISTORY"):
            self.run_job()
        self.assertEqual(self.fake.creates, 0)

    def test_active_or_unknown_own_candidate_status_never_exempts_identity(self):
        previous = {"story_id": self.item["story_id"], "inactive": True, "candidate_row_only": True}
        self.current_history["stories"] = [previous]
        for status in ("Published", "PUBLISHED", "Scheduled", "Pending", "", None, "unknown"):
            previous["status"] = status
            with self.subTest(status=status), self.assertRaisesRegex(p.Blocked, "INVALID_INACTIVE_HISTORY_EXEMPTION"):
                self.run_job()
        self.assertEqual(self.fake.creates, 0)

    def test_own_draft_with_active_or_unknown_provider_cannot_exempt_final_hash(self):
        previous = {"story_id": self.item["story_id"], "inactive": True, "candidate_row_only": True,
                    "status": "Draft", "final_sha256": self.item["final"]["sha256"],
                    "providers": [{"network": "youtube", "status": "Published"}]}
        self.current_history["stories"] = [previous]
        for status in ("Published", "PENDING", None):
            previous["providers"][0]["status"] = status
            with self.subTest(status=status), self.assertRaisesRegex(p.Blocked, "INVALID_INACTIVE_HISTORY_EXEMPTION"):
                self.run_job()
        self.assertEqual(self.fake.creates, 0)

    def test_explicit_inactive_candidate_can_still_release(self):
        self.current_history["stories"] = [{"story_id": self.item["story_id"], "inactive": True,
            "candidate_row_only": True, "status": "Draft", "final_sha256": self.item["final"]["sha256"]}]
        self.assertEqual(self.run_job()["state"], "SCHEDULED_PENDING")

    def test_unresolved_other_story_blocks_all_new_creates(self):
        db = pub.connection(self.journal)
        db.execute("INSERT INTO attempts VALUES (?,?,?,?,?,?,?,?)", ("other", "other", "other", "other", "other", "{}", "UNKNOWN_REQUIRES_RECONCILIATION", "{}"))
        db.commit(); db.close()
        with self.assertRaisesRegex(p.Blocked, "UNRESOLVED_PREVIOUS_WRITE"):
            self.run_job()
        self.assertEqual(self.fake.creates, 0)

    def test_previous_success_must_reach_all_external_histories(self):
        db = pub.connection(self.journal)
        db.execute("INSERT INTO attempts VALUES (?,?,?,?,?,?,?,?)", ("other", "other", "other", "other", "other", "{}", "SCHEDULED_PENDING", "{}"))
        db.commit(); db.close()
        for name in ("metricool", "notion"):
            self.current_history["sources"][name]["observed_delivery_keys"] = ["other"]
        with self.assertRaisesRegex(p.Blocked, "PREVIOUS_DELIVERY_NOT_RECONCILED:repository"):
            self.run_job()
        self.assertEqual(self.fake.creates, 0)

    def test_prior_success_must_be_included_in_current_day_queue_counts(self):
        payload = {"publicationDate": {"dateTime": "2026-10-09T06:00:00", "timezone": pub.ZONE},
                   "providers": [{"network": "youtube"}]}
        db = pub.connection(self.journal)
        db.execute("INSERT INTO attempts VALUES (?,?,?,?,?,?,?,?)", ("other", "other", "other", "other", "other",
            pub.canonical(payload), "PUBLISHED", "{}"))
        db.commit(); db.close()
        for name in ("metricool", "notion", "repository"):
            self.current_history["sources"][name]["observed_delivery_keys"] = ["other"]
        counts = self.current_history["queue_snapshot"]["platforms"]["youtube"]
        for published, observed in ((9, []), (0, ["other"])):
            counts.update(published=published, observed_delivery_keys=observed)
            with self.subTest(counts=counts.copy()), self.assertRaisesRegex(p.Blocked, "PREVIOUS_DELIVERY_NOT_INCLUDED_IN_QUEUE_COUNTS:youtube"):
                self.run_job()
        self.assertEqual(self.fake.creates, 0)
        counts.update(published=9, observed_delivery_keys=["other"])
        self.assertEqual(self.run_job()["state"], "SCHEDULED_PENDING")

    def test_prior_date_success_needs_archive_ack_but_not_today_count(self):
        payload = {"publicationDate": {"dateTime": "2026-10-08T06:00:00", "timezone": pub.ZONE},
                   "providers": [{"network": "youtube"}]}
        db = pub.connection(self.journal)
        db.execute("INSERT INTO attempts VALUES (?,?,?,?,?,?,?,?)", ("other", "other", "other", "other", "other",
            pub.canonical(payload), "PUBLISHED", "{}"))
        db.commit(); db.close()
        for name in ("metricool", "notion", "repository"):
            self.current_history["sources"][name]["observed_delivery_keys"] = ["other"]
        self.assertEqual(self.run_job()["state"], "SCHEDULED_PENDING")

    def test_changed_story_and_media_cannot_reuse_fingerprint_or_script(self):
        db = pub.connection(self.journal)
        for field in ("fingerprint", "script"):
            values = {"fingerprint": "other", "script": "other"}
            values[field] = p.normalized(self.item["fingerprint"]) if field == "fingerprint" else pub.normalized_script_hash(self.item)
            db.execute("INSERT INTO attempts VALUES (?,?,?,?,?,?,?,?)", ("other", "other", "other", values["fingerprint"], values["script"], "{}", "PUBLISHED", "{}"))
            db.commit()
            with self.assertRaisesRegex(p.Blocked, "ALREADY_ATTEMPTED_NO_RETRY"):
                self.run_job()
            db.execute("DELETE FROM attempts")  # test fixture only; no runtime reset exists
            db.commit()
        db.close()
        self.assertEqual(self.fake.creates, 0)


class RequestShapeTests(unittest.TestCase):
    def test_sparse_platform_payloads_and_no_second_music(self):
        item = {"title": "UNIT_TEST_FIXTURE", "delivery": {"media_url": "https://static.metricool.com/UNIT_TEST.mp4",
            "media_sha256": "a" * 64, "media_bytes": 12, "youtube_made_for_kids": False}}
        for platform in p.PLATFORMS:
            h = {"scheduled_at": "2026-10-11T07:00:00+03:00", "platform": platform, "caption": "UNIT_TEST", "media_sha256": "a" * 64}
            body = pub.post_info(item, h)
            self.assertEqual([k for k in body if k.endswith("Data")], [platform + "Data"])
            self.assertNotIn("id", body)
            self.assertNotIn("uuid", body)
            if platform == "tiktok":
                self.assertFalse(body["tiktokData"]["autoAddMusic"])

    def test_actual_mcp_envelope_forms_and_explicit_brand(self):
        rows = [{"id": 123, "brand_id": pub.BRAND}]
        self.assertEqual(pub.rows_from({"content": [{"type": "text", "text": json.dumps({"data": rows})}], "isError": False}), rows)
        self.assertEqual(pub.rows_from({"structuredContent": {"data": rows}, "isError": False}), rows)
        with self.assertRaisesRegex(p.Blocked, "LIVE_BRAND_MISMATCH"):
            pub.rows_from({"structuredContent": {"brandId": 1, "data": []}})

    def test_nested_and_snake_case_pagination_cannot_be_empty_success(self):
        for flags in ({"pagination": {"hasMore": True}}, {"has_more": True}, {"next_cursor": "remaining"}):
            with self.subTest(flags=flags), self.assertRaisesRegex(p.Blocked, "INCOMPLETE_METRICOOL"):
                pub.rows_from({"content": [{"type": "text", "text": json.dumps({"data": [], **flags})}]})


if __name__ == "__main__":
    unittest.main()
