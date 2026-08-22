"""Tests for the public static collector (no live network)."""
import unittest
from pathlib import Path

from constitutional_cms import collector, evaluator


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_HTML = (ROOT / "tests/fixtures/audit_page.html").read_text(encoding="utf-8")


def stub_fetch(body: str, status: int = 200, headers: dict | None = None):
    def _fetch(url: str, timeout: float) -> collector.FetchResult:
        return collector.FetchResult(
            url=url,
            final_url=url,
            status=status,
            headers={"content-type": "text/html; charset=utf-8", **(headers or {})},
            body=body.encode("utf-8"),
        )

    return _fetch


class DocumentParserTest(unittest.TestCase):
    def test_fixture_facts(self):
        facts = collector.parse_document(FIXTURE_HTML)
        self.assertEqual(facts.lang, "en")
        self.assertEqual(facts.canonical, "https://audit.example/guide")
        self.assertIn("index", facts.meta_robots)
        self.assertEqual(len(facts.jsonld_blocks), 1)
        self.assertTrue(collector.jsonld_single_unescape_ok(facts.jsonld_blocks[0]))

    def test_jsonld_entity_encoded_survives_single_unescape(self):
        self.assertTrue(collector.jsonld_single_unescape_ok('{&quot;a&quot;: 1}'))

    def test_jsonld_double_encoded_fails(self):
        self.assertFalse(collector.jsonld_single_unescape_ok("{&amp;quot;a&amp;quot;: 1}"))

    def test_jsonld_nonfinite_rejected(self):
        self.assertFalse(collector.jsonld_single_unescape_ok('{"a": NaN}'))


class CollectTest(unittest.TestCase):
    def test_bundle_is_schema_valid_and_evaluates(self):
        bundle = collector.collect(
            "https://audit.example/guide", fetch_fn=stub_fetch(FIXTURE_HTML)
        )
        evaluator.validate_instance(bundle, "evidence_bundle_v1.schema.json", "EvidenceBundleV1")

        receipt = evaluator.evaluate(evaluator.load_default_catalog(), bundle)
        verdicts = {check["check_id"]: check["verdict"] for check in receipt["checks"]}
        self.assertEqual(verdicts["web.http.success"], "PASS")
        self.assertEqual(verdicts["web.document.language"], "PASS")
        self.assertEqual(verdicts["search.canonical.absolute"], "PASS")
        self.assertEqual(verdicts["search.structured_data.jsonld_rfc8259"], "PASS")
        # Evidence a static GET cannot honestly provide stays UNMEASURED.
        self.assertEqual(verdicts["web.accessibility.automated"], "UNMEASURED")
        self.assertEqual(verdicts["web.performance.field_cwv"], "UNMEASURED")
        self.assertEqual(verdicts["search.robots.indexable"], "UNMEASURED")
        self.assertNotIn("FAIL", verdicts.values())

    def test_http_error_status_is_an_observation(self):
        bundle = collector.collect(
            "https://audit.example/missing", fetch_fn=stub_fetch("<html></html>", status=404)
        )
        receipt = evaluator.evaluate(evaluator.load_default_catalog(), bundle)
        verdicts = {check["check_id"]: check["verdict"] for check in receipt["checks"]}
        self.assertEqual(verdicts["web.http.success"], "FAIL")

    def test_noindex_header_marks_blocked(self):
        bundle = collector.collect(
            "https://audit.example/guide",
            fetch_fn=stub_fetch(FIXTURE_HTML, headers={"x-robots-tag": "noindex, nofollow"}),
        )
        self.assertTrue(bundle["observations"]["search"]["blocked"])

    def test_non_https_subject_rejected(self):
        with self.assertRaises(collector.CollectorError):
            collector.collect("http://audit.example/guide", fetch_fn=stub_fetch(FIXTURE_HTML))

    def test_missing_lang_and_canonical_stay_absent(self):
        bundle = collector.collect(
            "https://audit.example/bare",
            fetch_fn=stub_fetch("<!doctype html><html><body>hi</body></html>"),
        )
        self.assertNotIn("document", bundle["observations"])
        self.assertNotIn("canonical", bundle["observations"]["search"])
        self.assertFalse(bundle["observations"]["search"]["jsonld"]["present"])


if __name__ == "__main__":
    unittest.main()
