"""
Tests for the LLM prompt guardrails (TruthBeacon._build_prompt) and
the consensus equivalence principle (TruthBeacon.EQUIVALENCE_PRINCIPLE).

TestPromptGuardrails confirms every guardrail phrase claimed in the
README is actually present in the text sent to the model - turning
"the prompt instructs the model to..." from a documentation claim
into a checked property of the code.

TestEquivalencePrinciple confirms EQUIVALENCE_PRINCIPLE's field-name
references are consistent with nondet()'s actual JSON schema. This
class exists because an earlier draft of that constant referenced a
field name ('sources') that didn't actually exist in the payload it
was meant to judge (the real key is 'records') - a bug that a plain
Python exception would never have surfaced, since prompt_comparative
sends the principle text to an LLM comparator, not a parser.
"""

import unittest

from tests._bootstrap import TruthBeacon, make_contract

# Shared helper instance used to call former classmethod/staticmethod
# helpers, which are now plain instance methods (GenVM lint rule E022
# requires self as the first parameter on every gl.Contract method).
_helper = make_contract()


class TestPromptGuardrails(unittest.TestCase):
    """
    Pure function: _build_prompt(...) contains the required guardrail
    language.

    We cannot test real LLM compliance offline (no live model), but we
    CAN and do test that every guardrail this contract claims to
    enforce is actually present in the text sent to the model. This
    turns "the prompt instructs the model to..." from a README claim
    into a checked property of the code.
    """

    def setUp(self):
        self.prompt = _helper._build_prompt(
            "Example claim", "Example source content"
        )

    def test_contains_prompt_injection_guardrail(self):
        self.assertIn("NOT instructions", self.prompt)
        self.assertIn("HTML", self.prompt)
        self.assertIn("<script>", self.prompt)

    def test_contains_claim_text_injection_guardrail(self):
        # The claim text is just as attacker-controlled as source
        # content (anyone can call submit_claim with any claim_text),
        # so the injection guardrail must explicitly cover it too, not
        # just the fetched source content.
        self.assertIn("Both the claim text and the source content", self.prompt)
        self.assertIn("EITHER block", self.prompt)

    def test_contains_quoted_claim_guardrail(self):
        self.assertIn("QUOTED", self.prompt)

    def test_contains_opinion_guardrail(self):
        self.assertIn("OPINIONS", self.prompt)

    def test_contains_syndicated_copy_guardrail(self):
        self.assertIn("SYNDICATED", self.prompt)

    def test_contains_speculation_guardrail(self):
        self.assertIn("SPECULATIVE", self.prompt)

    def test_contains_insufficient_evidence_guardrail(self):
        self.assertIn("Do not guess", self.prompt)

    def test_fixed_output_vocabulary_still_present(self):
        # Strengthening the prompt must not have disturbed the fixed,
        # comparator-friendly output vocabulary.
        for word in ("Supported", "NotSupported", "Unclear"):
            self.assertIn(word, self.prompt)
        self.assertIn("ONLY one single word", self.prompt)


class TestEquivalencePrinciple(unittest.TestCase):
    """
    Pure sanity checks on EQUIVALENCE_PRINCIPLE: the natural-language
    principle text handed to gl.eq_principle.prompt_comparative must
    actually reference the real field names used in the JSON this
    contract's nondet() closure returns - a typo or drift here would
    silently make the comparator's job ill-defined without any Python
    exception ever being raised to catch it.
    """

    def test_references_actual_schema_fields(self):
        principle = TruthBeacon.EQUIVALENCE_PRINCIPLE
        for field_name in (
            "final_verdict",
            "fetch_status",
            "verdict",
            "records",
            "independent_domain_count",
            "duplicate_domain_count",
            "failed_source_count",
        ):
            self.assertIn(field_name, principle)

    def test_does_not_reference_the_wrong_persisted_field_name(self):
        # nondet() returns the per-source array under the key
        # "records"; only submit_claim's final on-chain persistence
        # step renames it to "sources" for the public get_claim() API.
        # EQUIVALENCE_PRINCIPLE is evaluated against nondet()'s raw
        # return value, so it must say "records", not "sources" - a
        # previous draft of this constant got this wrong. This test
        # exists specifically so that regression can't silently
        # reappear.
        import re

        principle = TruthBeacon.EQUIVALENCE_PRINCIPLE
        self.assertNotIn("'sources'", principle)
        self.assertIsNone(re.search(r"\bsources\b", principle))

    def test_is_a_non_trivial_string(self):
        # Guards against someone accidentally leaving this blank/None,
        # which would silently degrade prompt_comparative's guidance.
        self.assertIsInstance(TruthBeacon.EQUIVALENCE_PRINCIPLE, str)
        self.assertGreater(len(TruthBeacon.EQUIVALENCE_PRINCIPLE), 50)


if __name__ == "__main__":
    unittest.main(verbosity=2)
