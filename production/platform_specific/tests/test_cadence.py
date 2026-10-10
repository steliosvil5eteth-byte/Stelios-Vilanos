"""Cadence migration tests; local fixture manifests are not queue or QA evidence."""
import copy
import datetime as dt
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import pipeline as p
from test_pipeline import NOW, final_fixture, history, job, media_probe, policy


def legacy_manifest():
    old = p.scaffold("2026-10-09")
    old.update(program=p.LEGACY_PROGRAM, schema_version=1)
    old["jobs"] = [item for item in old["jobs"] if item["slot_local"] in p.LEGACY_SLOTS]
    return old


class CadenceTests(unittest.TestCase):
    def test_original_ten_times_and_ids_preserved_with_five_new_times(self):
        manifest = p.scaffold("2026-10-11")
        self.assertEqual(len(p.SLOTS), 15)
        self.assertEqual(len(set(p.SLOTS)), 15)
        self.assertEqual(p.SLOTS, tuple(sorted(p.SLOTS)))
        self.assertTrue(all("07:00" <= slot <= "22:00" for slot in p.SLOTS))
        for platform in p.PLATFORMS:
            for number, slot in enumerate(p.LEGACY_SLOTS, 1):
                item = next(j for j in manifest["jobs"] if j["platform"] == platform and j["slot_local"] == slot)
                self.assertEqual(item["id"], f"2026-10-11-{platform}-{number:02d}")

    def test_legacy_manifest_requires_explicit_copy_migration(self):
        old = legacy_manifest()
        old["jobs"][0]["final"] = {"path": "assets/exact.mp4", "sha256": "a" * 64}
        before = copy.deepcopy(old)
        self.assertIn("LEGACY_TEN_MANIFEST_REQUIRES_EXPLICIT_MIGRATION", p.validate_manifest(old))
        new = p.migrate_ten_manifest(old)
        self.assertEqual(old, before)
        self.assertEqual(p.validate_manifest(new), [])
        self.assertEqual(len(new["jobs"]), 60)
        self.assertEqual(new["local_date"], old["local_date"])
        self.assertFalse(new["counts_as_scheduled_queue"])
        for item in old["jobs"]:
            self.assertEqual(next(j for j in new["jobs"] if j["id"] == item["id"]), item)
        self.assertTrue(all(j["stage"] == "EMPTY_SLOT" and j["story_id"] is None
                            for j in new["jobs"] if j["slot_local"] in p.ADDITIONAL_SLOTS))

    def test_migration_cannot_overwrite_source_or_move_asset_base(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "legacy.json"
            p.write_json(source, legacy_manifest())
            before = source.read_bytes()
            for output in (source, Path(tmp) / "different" / "new.json"):
                with mock.patch("sys.argv", ["pipeline", "migrate-ten-manifest", "--manifest", str(source), "--output", str(output)]), mock.patch("builtins.print"):
                    self.assertEqual(p.main(), 2)
                self.assertEqual(source.read_bytes(), before)
            sibling = source.with_name("fifteen.json")
            with mock.patch("sys.argv", ["pipeline", "migrate-ten-manifest", "--manifest", str(source), "--output", str(sibling)]):
                self.assertEqual(p.main(), 0)
            self.assertEqual(source.read_bytes(), before)
            self.assertEqual(len(p.read_json(sibling)["jobs"]), 60)

    def test_migration_rejects_wrong_legacy_layout(self):
        old = legacy_manifest()
        old["jobs"][0]["slot_local"] = "23:00"
        with self.assertRaisesRegex(p.Blocked, "EXACT_LEGACY_TEN_SLOT_LAYOUT"):
            p.migrate_ten_manifest(old)

    def test_sixteenth_source_pack_is_not_silently_crossposted(self):
        manifest = p.scaffold("2026-10-09")
        catalog = [{"story_id": f"UNIT_TEST_{n}", "platform": "youtube"} for n in range(16)]
        with self.assertRaisesRegex(p.Blocked, "15 is the daily maximum"):
            p.import_catalog(manifest, catalog)
        self.assertEqual(sum(bool(j.get("story_id")) for j in manifest["jobs"]), 15)
        self.assertTrue(all(j["platform"] == "youtube" for j in manifest["jobs"] if j.get("story_id")))

    def test_relabeling_old_policy_does_not_change_its_cap(self):
        candidate = policy()
        candidate["targets"]["per_platform_daily_video_target"] = 10
        self.assertIn("CANONICAL_CADENCE_TARGETS_MISMATCH", p.production_errors(candidate, "youtube", "release"))
        candidate = policy()
        candidate["program_label"] = p.LEGACY_PROGRAM
        self.assertIn("CANONICAL_PROGRAM_DISABLED", p.production_errors(candidate, "youtube", "release"))
        candidate = policy()
        candidate["scheduling"]["proposed_local_slots"] = list(p.LEGACY_SLOTS)
        self.assertIn("CANONICAL_CADENCE_TARGETS_MISMATCH", p.production_errors(candidate, "youtube", "release"))

    def test_fourteen_allows_fifteenth_and_fifteen_blocks_sixteenth(self):
        item = job()
        receipt = history(item)
        for total in (10, 14, 15, 16):
            receipt["queue_snapshot"]["platforms"]["youtube"] = {"published": total - 2, "active_pending": 2}
            with self.subTest(total=total):
                errors = p.queue_capacity_errors(item, receipt, NOW)
                self.assertEqual(bool(errors), total >= 15)

    def test_quality_first_same_day_catch_up_keeps_safe_future_time(self):
        # UNIT_TEST_FIXTURE: original same-day catch-up remains valid after
        # the fifteen proposed editorial slots; it still makes no live write.
        now = dt.datetime(2026, 10, 9, 19, 5, tzinfo=p.UTC)  # 22:05 Athens
        item = job()
        item["slot_local"] = "22:30"
        manifest = p.scaffold(item["local_date"])
        manifest["jobs"][-p.DAILY_PER_PLATFORM] = item
        self.assertEqual(p.validate_manifest(manifest), [])
        receipt = history(item)
        receipt.update(checked_at=(now - dt.timedelta(minutes=1)).isoformat(), expires_at=(now + dt.timedelta(minutes=10)).isoformat())
        receipt["queue_snapshot"].update(checked_at=now.isoformat(), expires_at=(now + dt.timedelta(minutes=5)).isoformat())
        receipt["queue_snapshot"]["platforms"]["youtube"]["published"] = 14
        receipt["sources"]["production_lease"]["lease_expires_at"] = (now + dt.timedelta(minutes=10)).isoformat()
        receipt["semantic_reviews"][item["id"]]["checked_at"] = now.isoformat()
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            final_fixture(item, base)
            item["native_ai_disclosure"] = {"platform": "youtube", "verified": True, "evidence": "UNIT_TEST_FIXTURE"}
            with mock.patch("pipeline.probe_media", return_value=media_probe()):
                handoff = p.release_preflight(item, base, policy(), receipt, now)
            self.assertEqual(handoff["scheduled_at"], "2026-10-09T22:30:00+03:00")
            self.assertEqual(handoff["status"], "RELEASE_HANDOFF_ONLY_NOT_SCHEDULED")

    def test_sixty_empty_slots_are_zero_scheduled_posts(self):
        result = p.plan(p.scaffold("2026-10-11"), Path("."), policy(False), {}, {}, NOW)
        self.assertEqual(sum(v["slots"] for v in result["per_platform"].values()), 60)
        self.assertEqual(result["real_scheduled_queue_count"], 0)
        self.assertFalse(result["daily_complete"])
        self.assertEqual(result["new_publication_calls"], 0)

    def test_canonical_config_matches_cadence_and_remains_disabled(self):
        root = Path(__file__).resolve().parents[3]
        config = json.loads((root / "config/platform_growth_strategy.json").read_text())
        self.assertEqual(config["program_label"], p.PROGRAM)
        self.assertEqual(config["targets"]["per_platform_daily_video_target"], 15)
        self.assertEqual(config["targets"]["daily_distinct_stories"], 60)
        self.assertEqual(config["scheduling"]["proposed_local_slots"], list(p.SLOTS))
        for platform in config["platforms"].values():
            self.assertEqual(platform["daily_video_target"], 15)
            self.assertEqual(sum(x["count"] for x in platform["initial_daily_mix"]), 15)
            self.assertFalse(platform["enabled"])
        for key in ("enabled", "active_schedule"):
            self.assertFalse(config[key])
        self.assertFalse(config["scheduling"]["enabled"])
        self.assertFalse(config["production"]["publication_enabled"])
        self.assertFalse(config["production"]["new_media_enabled"])
        self.assertEqual(config["routing"]["active_publish_providers"], [])

    def test_compatibility_routing_mirrors_match_without_enabling_routes(self):
        root = Path(__file__).resolve().parents[3]
        for filename in ("content_strategy", "integrations", "publishing_reliability", "youtube_growth_strategy"):
            config = json.loads((root / f"config/{filename}.json").read_text())
            base = config["publishing"] if filename == "integrations" else config
            route = base["provider_routing_override"]
            with self.subTest(filename=filename):
                self.assertEqual(route["program_label"], p.PROGRAM)
                self.assertEqual(route["required_program_attribution"], p.PROGRAM)
                self.assertEqual(route["objective_distinct_videos_per_day"], 60)
                self.assertEqual(route["objective_destinations_per_day"], 60)
                self.assertEqual(route["objective_videos_per_platform_per_day"], dict.fromkeys(p.PLATFORMS, 15))
                self.assertFalse(route["enabled"])
                self.assertEqual(route["allowed_providers"], [])
                self.assertFalse(route["broadcast_fallback_allowed"])
                self.assertFalse(route["crossposting_allowed"])

    def test_completion_gate_uses_fifteen_sixty_and_preserves_pending_distinction(self):
        root = Path(__file__).resolve().parents[3]
        config = json.loads((root / "config/publishing_reliability.json").read_text())
        self.assertNotIn("ten_slot_integrity_gate", config)
        gate = config["daily_slot_integrity_gate"]
        self.assertTrue(gate["require_exactly_fifteen_verified_videos_per_platform_for_completion"])
        self.assertTrue(gate["require_sixty_distinct_stories_and_final_media_for_completion"])
        self.assertEqual(gate["expected_physical_member_posts_per_platform_per_day"], 15)
        self.assertEqual(gate["expected_destinations_per_day"], 60)
        self.assertEqual(gate["daily_completion_accepted_provider_status"], "PUBLISHED")
        self.assertFalse(gate["scheduled_pending_counts_as_published"])


if __name__ == "__main__":
    unittest.main()
