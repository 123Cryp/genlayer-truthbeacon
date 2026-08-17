"""
Tests for deterministic verdict aggregation (TruthBeacon._aggregate).

Covers every branch of the FINAL_VERDICTS decision rule (Verified /
Refuted / Disputed / Unverified / InsufficientEvidence) at the pure
function level, including the majority-with-dissent edge case and the
low-credibility/duplicate-domain exclusions. See README "Aggregation
logic, made unambiguous" for the exact decision table this pins down.
"""

import unittest

from tests._bootstrap import TruthBeacon, make_contract

# Shared helper instance used to call former classmethod/staticmethod
# helpers, which are now plain instance methods (GenVM lint rule E022
# requires self as the first parameter on every gl.Contract method).
_helper = make_contract()


class TestAggregation(unittest.TestCase):
    """Pure function: per-source records -> single final verdict."""

    def _rec(
        self,
        verdict,
        domain,
        status="ok",
        dup=False,
        low_cred=False,
        stale=False,
        authorized=True,
    ):
        # `stale` / `authorized` default to the values that preserve
        # pre-v2.8 behavior (not stale, authorized) so every
        # pre-existing call site below - which doesn't pass these two
        # new kwargs at all - is completely unaffected.
        return {
            "url": f"https://{domain}/a",
            "domain": domain,
            "is_duplicate_domain": dup,
            "is_low_credibility": low_cred,
            "fetch_status": status,
            "verdict": verdict,
            "is_stale": stale,
            "is_authorized_domain": authorized,
        }

    def test_two_independent_supports_yields_verified(self):
        records = [
            self._rec("Supported", "a.com"),
            self._rec("Supported", "b.com"),
        ]
        self.assertEqual(_helper._aggregate(records), "Verified")

    def test_two_independent_opposes_yields_refuted(self):
        records = [
            self._rec("NotSupported", "a.com"),
            self._rec("NotSupported", "b.com"),
        ]
        self.assertEqual(_helper._aggregate(records), "Refuted")

    def test_conflicting_evidence_yields_disputed(self):
        records = [
            self._rec("Supported", "a.com"),
            self._rec("NotSupported", "b.com"),
        ]
        self.assertEqual(_helper._aggregate(records), "Disputed")

    def test_majority_with_dissent_still_verifies(self):
        # Two independent sources support the claim, one independent
        # source refutes it. Because "Verified" requires at least two
        # independent supporting sources AND more support than
        # opposition (not unanimity), this reaches a clear majority
        # and is "Verified" rather than "Disputed". This is a
        # deliberate design choice - see README "Aggregation logic,
        # made unambiguous" - and is documented here so the behavior
        # is pinned down by a test, not just left implicit in
        # _aggregate's control flow.
        records = [
            self._rec("Supported", "a.com"),
            self._rec("Supported", "b.com"),
            self._rec("NotSupported", "c.com"),
        ]
        self.assertEqual(_helper._aggregate(records), "Verified")

    def test_duplicate_domain_not_counted_as_corroboration(self):
        # Same domain twice: second is flagged as duplicate and must
        # NOT let a single publisher masquerade as two independent
        # sources.
        records = [
            self._rec("Supported", "a.com"),
            self._rec("Supported", "a.com", dup=True),
        ]
        self.assertEqual(_helper._aggregate(records), "InsufficientEvidence")

    def test_low_credibility_source_cannot_verify_alone(self):
        records = [
            self._rec("Supported", "faux-news.example", low_cred=True),
        ]
        self.assertEqual(_helper._aggregate(records), "InsufficientEvidence")

    def test_low_credibility_source_excluded_even_with_one_real_source(self):
        # One real independent source + one fake-news source agreeing
        # is still only ONE independent, credible source - not enough
        # to reach "Verified" on its own.
        records = [
            self._rec("Supported", "real-news.example"),
            self._rec("Supported", "faux-news.example", low_cred=True),
        ]
        self.assertEqual(_helper._aggregate(records), "InsufficientEvidence")

    def test_all_failed_fetches_yields_insufficient_evidence(self):
        records = [
            self._rec("NoEvidence", "a.com", status="timeout"),
            self._rec("NoEvidence", "b.com", status="inaccessible"),
            self._rec("NoEvidence", "c.com", status="empty"),
        ]
        self.assertEqual(_helper._aggregate(records), "InsufficientEvidence")

    def test_mostly_unclear_yields_unverified(self):
        records = [
            self._rec("Unclear", "a.com"),
            self._rec("Unclear", "b.com"),
        ]
        self.assertEqual(_helper._aggregate(records), "Unverified")

    # --- v2.8: freshness gating (see CHANGELOG.md) ---

    def test_stale_source_not_counted_as_corroboration(self):
        # Two supporting sources, but one is explicitly flagged stale
        # - same exclusion shape as the existing duplicate-domain
        # test: a stale source must not be able to prop up a verdict
        # any more than a duplicate-domain one can.
        records = [
            self._rec("Supported", "a.com"),
            self._rec("Supported", "b.com", stale=True),
        ]
        self.assertEqual(_helper._aggregate(records), "InsufficientEvidence")

    def test_undated_source_excluded_same_as_stale(self):
        # "Undated" is folded into is_stale=True by the nondet()
        # closure in submit_claim (see _parse_freshness_label /
        # is_stale computation) before records ever reach
        # _aggregate, so at this pure-function level "undated" and
        # "stale" are indistinguishable - both just set is_stale=True.
        records = [
            self._rec("Supported", "a.com"),
            self._rec("Supported", "b.com", stale=True),
            self._rec("Supported", "c.com", stale=True),
        ]
        self.assertEqual(_helper._aggregate(records), "InsufficientEvidence")

    def test_two_fresh_supports_still_verify_with_a_stale_third(self):
        # A stale source among otherwise-sufficient fresh corroboration
        # doesn't poison the whole result - it's simply excluded, and
        # the remaining two fresh, independent supports are enough on
        # their own.
        records = [
            self._rec("Supported", "a.com"),
            self._rec("Supported", "b.com"),
            self._rec("Supported", "c.com", stale=True),
        ]
        self.assertEqual(_helper._aggregate(records), "Verified")

    def test_missing_freshness_key_defaults_to_not_stale(self):
        # Backward compatibility: a record dict built without the
        # is_stale key at all (as every record did before v2.8) must
        # behave exactly as it did before - _aggregate reads it via
        # `.get("is_stale", False)`, never raises KeyError, and
        # treats the source as eligible.
        records = [
            {
                "url": "https://a.com/x",
                "domain": "a.com",
                "is_duplicate_domain": False,
                "is_low_credibility": False,
                "fetch_status": "ok",
                "verdict": "Supported",
            },
            {
                "url": "https://b.com/x",
                "domain": "b.com",
                "is_duplicate_domain": False,
                "is_low_credibility": False,
                "fetch_status": "ok",
                "verdict": "Supported",
            },
        ]
        self.assertEqual(_helper._aggregate(records), "Verified")

    # --- v2.8: source-authority gating (see CHANGELOG.md) ---

    def test_unauthorized_domain_not_counted_as_corroboration(self):
        # A source outside the claim's declared expected_domains
        # policy must not be able to count toward corroboration, even
        # if it's otherwise a perfectly healthy, credible, fresh
        # source.
        records = [
            self._rec("Supported", "a.com"),
            self._rec("Supported", "b.com", authorized=False),
        ]
        self.assertEqual(_helper._aggregate(records), "InsufficientEvidence")

    def test_missing_authorized_key_defaults_to_authorized(self):
        # Same backward-compatibility guarantee as is_stale: a record
        # dict without is_authorized_domain at all behaves exactly as
        # it did before v2.8 - fully eligible.
        records = [
            {
                "url": "https://a.com/x",
                "domain": "a.com",
                "is_duplicate_domain": False,
                "is_low_credibility": False,
                "fetch_status": "ok",
                "verdict": "Supported",
            },
            {
                "url": "https://b.com/x",
                "domain": "b.com",
                "is_duplicate_domain": False,
                "is_low_credibility": False,
                "fetch_status": "ok",
                "verdict": "Supported",
            },
        ]
        self.assertEqual(_helper._aggregate(records), "Verified")


if __name__ == "__main__":
    unittest.main(verbosity=2)
