"""
Tests for submit_claim's deterministic, pre-fetch input validation:
source-count bounds, claim-text / URL length limits, the
distinct-non-denylisted-domain requirement, and that validation
failures raise gl.vm.UserError specifically (GenLayer's documented
convention for user-facing errors) rather than a bare Exception.

These all run BEFORE any gl.nondet.* call, so no mocking is needed -
they exercise real submit_claim() calls end-to-end for the reject
path, and one success-path boundary check.
"""

import unittest
from unittest.mock import patch

from tests._bootstrap import TruthBeacon, gl, make_contract


class TestSubmitClaimInputValidation(unittest.TestCase):
    """Deterministic, pre-fetch input validation."""

    def test_rejects_single_source(self):
        c = make_contract()
        with self.assertRaises(Exception):
            c.submit_claim("The sky is blue", ["https://example.com/a"])

    def test_rejects_too_many_sources(self):
        c = make_contract()
        urls = [f"https://site{i}.com/a" for i in range(10)]
        with self.assertRaises(Exception):
            c.submit_claim("The sky is blue", urls)

    def test_rejects_duplicate_domains_only(self):
        c = make_contract()
        urls = [
            "https://example.com/a",
            "https://example.com/b",
            "https://www.example.com/c",  # same domain after normalization
        ]
        with self.assertRaises(Exception):
            c.submit_claim("The sky is blue", urls)

    def test_rejects_empty_claim_text(self):
        c = make_contract()
        urls = [
            "https://a.com/x",
            "https://b.com/x",
            "https://c.com/x",
        ]
        with self.assertRaises(Exception):
            c.submit_claim("   ", urls)

    def test_rejects_overly_long_claim_text(self):
        c = make_contract()
        urls = ["https://a.com/x", "https://b.com/x", "https://c.com/x"]
        too_long = "x" * (TruthBeacon.MAX_CLAIM_TEXT_CHARS + 1)
        with self.assertRaises(Exception):
            c.submit_claim(too_long, urls)

    def test_accepts_claim_text_at_exact_length_limit(self):
        c = make_contract()
        urls = ["https://a.com/x", "https://b.com/x", "https://c.com/x"]
        exactly_at_limit = "x" * TruthBeacon.MAX_CLAIM_TEXT_CHARS

        def fetch(url, mode="text"):
            return "A sufficiently long, legitimate article body. " * 3

        def prompt(p, response_format="text"):
            return "Supported"

        with patch.object(gl.nondet.web, "render", side_effect=fetch), patch.object(
            gl.nondet, "exec_prompt", side_effect=prompt
        ):
            # Must not raise.
            c.submit_claim(exactly_at_limit, urls)

    def test_overly_long_url_is_treated_as_invalid_not_fetched(self):
        # An absurdly long URL is rejected at the domain-extraction
        # stage (treated like an invalid scheme: never fetched) rather
        # than causing an error or being passed to gl.nondet.web.render.
        too_long_url = "https://example.com/" + ("a" * TruthBeacon.MAX_URL_CHARS)
        c = make_contract()
        self.assertEqual(c._extract_domain(too_long_url), "")

    def test_submission_entirely_of_low_credibility_domains_is_rejected(self):
        c = make_contract()
        urls = [
            "https://theonion.com/a",
            "https://clickhole.com/b",
            "https://thebeaverton.com/c",
        ]
        with self.assertRaises(Exception):
            c.submit_claim("Some claim", urls)

    def test_validation_errors_are_gl_user_errors(self):
        # GenLayer's documented convention is to raise gl.vm.UserError
        # (not a bare Exception) for user-facing validation failures,
        # so that GenVM can distinguish "the caller did something
        # invalid" from an actual contract bug. Pin this down
        # explicitly rather than just relying on `assertRaises(Exception)`
        # (which would also pass for a plain Exception).
        c = make_contract()
        with self.assertRaises(gl.vm.UserError):
            c.submit_claim("The sky is blue", ["https://example.com/a"])
        with self.assertRaises(gl.vm.UserError):
            c.get_claim("does-not-exist")


if __name__ == "__main__":
    unittest.main(verbosity=2)
