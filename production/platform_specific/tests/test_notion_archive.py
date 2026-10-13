"""UNIT_TEST_FIXTURE responses; no credentials, archive edits or live calls."""
import copy
import datetime as dt
import json
import unittest

import notion_archive as n

NOW = dt.datetime(2026, 10, 10, 14, 30, tzinfo=dt.timezone.utc)
SCHEMA = {"name": "UNIT_TEST_FIXTURE", "url": n.DATA_SOURCE,
          "schema": {"Title": {"type": "title"}, "Script": {"type": "text"},
                     "Status": {"type": "select"}, "Fingerprint": {"type": "text"}}}
VIEW = {"dataSourceUrl": "{{" + n.DATA_SOURCE + "}}", "type": "table",
        "name": "Default view", "displayProperties": list(SCHEMA["schema"])}


def envelope(value, structured=False):
    result = {"content": [{"type": "text", "text": json.dumps(value)}], "isError": False}
    if structured:
        result["structuredContent"] = copy.deepcopy(value)
    return result


def schema_response(state=None, structured=True):
    state = copy.deepcopy(SCHEMA if state is None else state)
    text = ('<data-source url="{{' + n.DATA_SOURCE + '}}">\n'
            '<data-source-state>\n' + json.dumps(state) + '\n</data-source-state>\n</data-source>')
    return envelope({"id": n.DATA_SOURCE, "text": text, "metadata": {"type": "data_source"}}, structured)


def view_response(settings=None):
    settings = copy.deepcopy(VIEW if settings is None else settings)
    text = ('Here is the result of "fetch" for the View with URL {{' + n.VIEW + '}}:\n'
            '<view url="{{' + n.VIEW + '}}">\n' + json.dumps(settings) + '\n</view>')
    return envelope({"id": n.VIEW, "text": text, "metadata": {"type": "view"}}, True)


def row(number=1):
    return {"url": f"https://app.notion.com/p/{number:032x}", "Title": "UNIT_TEST_FIXTURE",
            "Script": "Λέξεις<br><br>[πηγή](https://example.test/source) \\| formatting",
            "Status": "Published", "Fingerprint": "UNIT_TEST\\|story",
            "date:Publish Date:start": "2026-10-09", "Platforms": '["YouTube"]'}


def page(rows=(), more=False, cursor=None, **extra):
    return envelope({"results": list(rows), "has_more": more, "next_cursor": cursor, **extra})


class FakeTool:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, name, arguments):
        self.calls.append((name, copy.deepcopy(arguments)))
        if not self.responses:
            raise AssertionError("UNEXPECTED_EXTRA_CALL")
        value = self.responses.pop(0)
        if isinstance(value, Exception):
            raise value
        return copy.deepcopy(value)


def fixture(*pages, final_schema=None, final_view=None):
    return FakeTool([schema_response(), view_response(), *pages,
                     schema_response(final_schema), view_response(final_view)])


def collect(fake, **kwargs):
    return n.collect_archive(fake, clock=lambda: NOW, **kwargs)


class NotionArchiveTests(unittest.TestCase):
    def test_exact_connected_requests_exhaust_both_partitions_and_preserve_rows(self):
        original = row()
        fake = fixture(page([original], True, "active-next"), page([row(2)]),
                       page([row(3)], True, "archived-next"), page([row(4)]))
        result = collect(fake, page_size=2)
        self.assertEqual(result["pages_read"], {"active": 2, "archived": 2})
        self.assertEqual(result["rows_seen"], 4)
        self.assertEqual(result["active_rows"][0], original)
        self.assertEqual(result["archived_rows"], [row(3), row(4)])
        expected = []
        for archived, cursor in ((False, None), (False, "active-next"),
                                 (True, None), (True, "archived-next")):
            data = {"mode": "view", "view_url": n.VIEW, "page_size": 2, "is_archived": archived}
            if cursor:
                data["start_cursor"] = cursor
            expected.append((n.QUERY_TOOL, {"data": data}))
        self.assertEqual(fake.calls[2:6], expected)
        self.assertEqual(fake.calls[:2], [(n.FETCH_TOOL, {"id": n.DATA_SOURCE}),
                                          (n.FETCH_TOOL, {"id": n.VIEW})])
        self.assertEqual(fake.calls[-2:], fake.calls[:2])
        self.assertTrue(result["pagination_exhausted"])
        self.assertFalse(result["atomic_snapshot"])
        self.assertFalse(result["release_clearance"])
        for key in ("complete", "status", "expires_at", "observed_delivery_keys", "PASSED_FINAL_REVIEW"):
            self.assertNotIn(key, result)
        self.assertEqual(result["rows_sha256"], n.digest({"active": [row(), row(2)], "archived": [row(3), row(4)]}))
        self.assertTrue(all(name in {n.FETCH_TOOL, n.QUERY_TOOL} for name, _ in fake.calls))
        self.assertEqual(fake.responses, [])

    def test_empty_intermediate_page_still_continues(self):
        fake = fixture(page([], True, "empty-next"), page([row()]), page())
        self.assertEqual(collect(fake)["rows_seen"], 1)
        self.assertEqual(fake.calls[3][1]["data"]["start_cursor"], "empty-next")

    def test_fetch_text_envelope_without_structured_content_is_supported(self):
        fake = fixture(page(), page())
        fake.responses[0] = schema_response(structured=False)
        self.assertEqual(collect(fake)["rows_seen"], 0)

    def test_filtered_wrong_source_or_unrecognized_view_blocks_before_query(self):
        cases = [({**VIEW, "advancedFilter": {"property": "Status", "value": "Published"}}, "UNFILTERED"),
                 ({**VIEW, "filter": {"archived": False}}, "UNFILTERED"),
                 ({**VIEW, "dataSourceUrl": "collection://wrong"}, "SOURCE_MISMATCH"),
                 ({**VIEW, "futureFilterSetting": True}, "UNRECOGNIZED"),
                 ({**VIEW, "displayProperties": ["Title"]}, "FULL_SCHEMA")]
        for settings, code in cases:
            with self.subTest(code=code):
                fake = FakeTool([schema_response(), view_response(settings)])
                with self.assertRaisesRegex(n.ArchiveReadBlocked, code):
                    collect(fake)
                self.assertEqual(len(fake.calls), 2)

    def test_missing_or_wrong_schema_entity_blocks_before_query(self):
        response = schema_response()
        response["structuredContent"]["id"] = "collection://wrong"
        fake = FakeTool([response])
        with self.assertRaisesRegex(n.ArchiveReadBlocked, "ENTITY_BINDING"):
            collect(fake)
        self.assertEqual(len(fake.calls), 1)

    def test_partial_or_errored_envelope_is_never_complete(self):
        responses = [{"isError": True, "content": [{"type": "text", "text": "private detail"}]},
                     {**schema_response(), "truncated": True},
                     {**schema_response(), "unknown_block_count": 1}]
        for response in responses:
            with self.subTest(response_keys=list(response)):
                fake = FakeTool([response])
                with self.assertRaises(n.ArchiveReadBlocked) as ctx:
                    collect(fake)
                self.assertNotIn("private detail", str(ctx.exception))
                self.assertEqual(len(fake.calls), 1)

    def test_pagination_shape_cursor_and_unobserved_nested_envelope_fail_closed(self):
        cases = [(page([], True, None), "NEXT_CURSOR"), (page([], True, 4), "NEXT_CURSOR"),
                 (page([], False, "remaining"), "CONTRADICTORY_END"),
                 (page([], 0), "PAGINATION_SHAPE"),
                 (page([], pagination={"hasMore": True}), "PAGINATION_SHAPE"),
                 (envelope({"results": {}, "has_more": False}), "PAGINATION_SHAPE")]
        for bad, code in cases:
            with self.subTest(code=code):
                fake = fixture(bad)
                with self.assertRaisesRegex(n.ArchiveReadBlocked, code):
                    collect(fake)
                self.assertEqual(len(fake.calls), 3)

    def test_repeated_cursor_stops_without_blind_retry(self):
        fake = fixture(page([], True, "same"), page([], True, "same"))
        with self.assertRaisesRegex(n.ArchiveReadBlocked, "CURSOR_LOOP"):
            collect(fake)
        self.assertEqual(len(fake.calls), 4)

    def test_duplicate_identity_across_archived_partitions_blocks(self):
        duplicate = row()
        duplicate["url"] = "https://www.notion.so/UNIT_TEST-00000000-0000-0000-0000-000000000001"
        fake = fixture(page([row()]), page([duplicate]))
        with self.assertRaisesRegex(n.ArchiveReadBlocked, "DUPLICATE_PAGE_ID"):
            collect(fake)

    def test_late_callback_error_returns_no_partial_result_or_private_body(self):
        fake = fixture(page([row()], True, "next"), RuntimeError("Bearer UNIT_TEST_SECRET"))
        with self.assertRaisesRegex(n.ArchiveReadBlocked, "^NOTION_READ_CALL_FAILED$"):
            collect(fake)
        self.assertEqual(len(fake.calls), 4)
        self.assertEqual(len(fake.responses), 2)

    def test_view_filter_or_schema_change_during_read_blocks(self):
        fake = fixture(page(), page(), final_view={**VIEW, "filter": {"status": "Published"}})
        with self.assertRaisesRegex(n.ArchiveReadBlocked, "UNFILTERED"):
            collect(fake)
        fake = fixture(page(), page(), final_schema={**SCHEMA, "name": "UNIT_TEST_CHANGED"})
        with self.assertRaisesRegex(n.ArchiveReadBlocked, "CHANGED_DURING_READ"):
            collect(fake)

    def test_page_and_row_bounds_fail_instead_of_claiming_partial_completion(self):
        fake = fixture(page([], True, "next"), page())
        with self.assertRaisesRegex(n.ArchiveReadBlocked, "PAGE_LIMIT"):
            collect(fake, max_pages=2)
        self.assertEqual(len(fake.calls), 4)
        fake = fixture(page([row(), row(2)]))
        with self.assertRaisesRegex(n.ArchiveReadBlocked, "ROW_LIMIT"):
            collect(fake, max_rows=1)

    def test_page_identity_requires_a_real_notion_page_url(self):
        for url in ("https://example.test/" + "1" * 32, "https://app.notion.com/p/" + "1" * 33,
                    "https://user:password@app.notion.com/p/" + "1" * 32):
            with self.subTest(url=url):
                fake = fixture(page([{**row(), "url": url}]))
                with self.assertRaisesRegex(n.ArchiveReadBlocked, "ROW_URL_INVALID"):
                    collect(fake)

    def test_receipt_clock_cannot_be_naive_or_move_backward(self):
        fake = fixture(page(), page())
        with self.assertRaisesRegex(n.ArchiveReadBlocked, "AWARE_CLOCK"):
            n.collect_archive(fake, clock=lambda: NOW.replace(tzinfo=None))
        self.assertEqual(fake.calls, [])
        times = iter([NOW, NOW - dt.timedelta(seconds=1)])
        with self.assertRaisesRegex(n.ArchiveReadBlocked, "CLOCK_MOVED_BACKWARD"):
            n.collect_archive(fake, clock=lambda: next(times))
        self.assertEqual(len(fake.calls), 1)


if __name__ == "__main__":
    unittest.main()
