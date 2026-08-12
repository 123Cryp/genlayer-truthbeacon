"""
Tests for on-chain storage / view methods: get_claim, get_verdict,
total_claims, and multi-claim persistence.

TestViewMethods covers the two accessor methods in isolation.
TestStoragePersistence goes further and specifically verifies that
MULTIPLE claims submitted to the SAME contract instance remain
independently and correctly retrievable afterward (i.e. claim_records
is keyed correctly and claim N's data is never overwritten or
corrupted by claim N+1) - the kind of storage-isolation bug that
per-helper unit tests would never catch, since each of those only
ever exercises a single claim in isolation.
"""

import json
import unittest
from unittest.mock import patch

from tests._bootstrap import TruthBeacon, gl, make_contract


class TestViewMethods(unittest.TestCase):
    def test_get_claim_unknown_id_raises(self):
        c = make_contract()
        with self.assertRaises(Exception):
            c.get_claim("999")

    def test_get_verdict_unknown_id_raises(self):
        c = make_contract()
        with self.assertRaises(Exception):
            c.get_verdict("999")

    def test_total_claims_starts_at_zero(self):
        c = make_contract()
        self.assertEqual(c.total_claims(), 0)

    def test_total_claims_increments(self):
        c = make_contract()
        urls = ["https://a.com/x", "https://b.com/x", "https://c.com/x"]

        def fetch(url, mode="text"):
            return "A sufficiently long, legitimate article body. " * 3

        def prompt(p, response_format="text"):
            return "Supported"

        with patch.object(gl.nondet.web, "render", side_effect=fetch), patch.object(
            gl.nondet, "exec_prompt", side_effect=prompt
        ):
            self.assertEqual(c.total_claims(), 0)
            c.submit_claim("claim one", urls)
            self.assertEqual(c.total_claims(), 1)
            c.submit_claim("claim two", urls)
            self.assertEqual(c.total_claims(), 2)


class TestStoragePersistence(unittest.TestCase):
    """
    Multi-claim storage isolation: submitting several claims to the
    same contract instance must never let one claim's data leak into,
    overwrite, or otherwise corrupt another's.
    """

    def setUp(self):
        self.contract = make_contract()

    def _submit(self, claim_text, urls, verdict_word):
        def fetch(url, mode="text"):
            return "A sufficiently long, legitimate article body. " * 3

        def prompt(p, response_format="text"):
            return verdict_word

        with patch.object(
            gl.nondet.web, "render", side_effect=fetch
        ), patch.object(gl.nondet, "exec_prompt", side_effect=prompt):
            return self.contract.submit_claim(claim_text, urls)

    def test_sequential_claim_ids_are_assigned(self):
        urls = ["https://a.com/x", "https://b.com/x", "https://c.com/x"]
        id_0 = self._submit("First claim", urls, "Supported")
        id_1 = self._submit("Second claim", urls, "Supported")
        id_2 = self._submit("Third claim", urls, "Supported")
        self.assertEqual([id_0, id_1, id_2], ["0", "1", "2"])

    def test_multiple_claims_remain_independently_retrievable(self):
        # Three DIFFERENT claims, submitted with different verdict
        # outcomes, using overlapping-but-not-identical URL sets.
        # Every claim's stored record must reflect ITS OWN claim text
        # and verdict - never another claim's.
        id_verified = self._submit(
            "The sky is blue",
            ["https://a.com/x", "https://b.com/x", "https://c.com/x"],
            "Supported",
        )
        id_refuted = self._submit(
            "The moon is made of cheese",
            ["https://d.com/x", "https://e.com/x", "https://f.com/x"],
            "NotSupported",
        )
        id_disputed_setup = self._submit(
            "A contested claim",
            ["https://g.com/x", "https://h.com/x", "https://i.com/x"],
            "Unclear",
        )

        verified_record = json.loads(self.contract.get_claim(id_verified))
        refuted_record = json.loads(self.contract.get_claim(id_refuted))
        unverified_record = json.loads(self.contract.get_claim(id_disputed_setup))

        self.assertEqual(verified_record["claim_text"], "The sky is blue")
        self.assertEqual(verified_record["final_verdict"], "Verified")

        self.assertEqual(refuted_record["claim_text"], "The moon is made of cheese")
        self.assertEqual(refuted_record["final_verdict"], "Refuted")

        self.assertEqual(unverified_record["claim_text"], "A contested claim")
        self.assertEqual(unverified_record["final_verdict"], "Unverified")

        # Cross-check: no claim's stored text or verdict leaked into
        # another claim's record.
        all_texts = {
            verified_record["claim_text"],
            refuted_record["claim_text"],
            unverified_record["claim_text"],
        }
        self.assertEqual(len(all_texts), 3)

    def test_get_verdict_matches_final_verdict_inside_get_claim(self):
        # get_verdict() is a convenience accessor over the same
        # underlying stored record get_claim() returns - the two must
        # never disagree.
        claim_id = self._submit(
            "Some claim",
            ["https://a.com/x", "https://b.com/x", "https://c.com/x"],
            "Supported",
        )
        full_record = json.loads(self.contract.get_claim(claim_id))
        self.assertEqual(self.contract.get_verdict(claim_id), full_record["final_verdict"])

    def test_earlier_claim_unaffected_by_later_submission(self):
        # Regression guard for the specific failure mode of a shared
        # mutable dict/list being accidentally reused across
        # submissions instead of each claim getting its own data.
        urls = ["https://a.com/x", "https://b.com/x", "https://c.com/x"]
        first_id = self._submit("First claim", urls, "Supported")
        first_record_before = self.contract.get_claim(first_id)

        self._submit("Second claim", urls, "NotSupported")
        self._submit("Third claim", urls, "Unclear")

        first_record_after = self.contract.get_claim(first_id)
        self.assertEqual(first_record_before, first_record_after)


if __name__ == "__main__":
    unittest.main(verbosity=2)
