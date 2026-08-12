"""
Tests for raw-LLM-response parsing (TruthBeacon._parse_source_verdict).

Covers exact matching, case-insensitivity, trailing punctuation,
answers that appear on a later line (model added a preamble despite
instructions), the whitespace-tolerant "Not Supported" == "NotSupported"
fix, and the false-positive guard against the verdict word appearing
merely as a substring of a longer explanatory sentence.
"""

import unittest

from tests._bootstrap import TruthBeacon, make_contract

# Shared helper instance used to call former classmethod/staticmethod
# helpers, which are now plain instance methods (GenVM lint rule E022
# requires self as the first parameter on every gl.Contract method).
_helper = make_contract()


class TestParseSourceVerdict(unittest.TestCase):
    """Pure function: raw LLM text -> one of Supported/NotSupported/Unclear."""

    def test_exact_match(self):
        self.assertEqual(_helper._parse_source_verdict("Supported"), "Supported")
        self.assertEqual(
            _helper._parse_source_verdict("NotSupported"), "NotSupported"
        )
        self.assertEqual(_helper._parse_source_verdict("Unclear"), "Unclear")

    def test_case_insensitive(self):
        self.assertEqual(_helper._parse_source_verdict("supported"), "Supported")
        self.assertEqual(_helper._parse_source_verdict("SUPPORTED"), "Supported")

    def test_trailing_punctuation_stripped(self):
        self.assertEqual(_helper._parse_source_verdict("Supported."), "Supported")
        self.assertEqual(_helper._parse_source_verdict('"Supported"'), "Supported")

    def test_not_supported_with_internal_space_is_recognized(self):
        # "NotSupported" is an unusual concatenated word; a model is
        # likely to naturally write "Not Supported" with a space
        # despite being shown the exact literal. This must still be
        # recognized rather than silently downgraded to "Unclear".
        self.assertEqual(
            _helper._parse_source_verdict("Not Supported"), "NotSupported"
        )
        self.assertEqual(
            _helper._parse_source_verdict("  Not   Supported  "),
            "NotSupported",
        )

    def test_answer_on_later_line_is_found(self):
        # A model that ignores the single-word instruction and adds a
        # preamble should still be read correctly if the actual
        # answer appears alone on its own line further down.
        raw = "I have reviewed the source carefully.\n\nSupported"
        self.assertEqual(_helper._parse_source_verdict(raw), "Supported")

    def test_word_as_substring_of_explanation_does_not_false_positive(self):
        # "unclear" appears INSIDE a longer sentence here, not as its
        # own line - must not be misread as a clean "Unclear" verdict
        # when no line actually IS just "Unclear".
        raw = "This is somewhat unclear in tone, but Supported overall."
        self.assertEqual(_helper._parse_source_verdict(raw), "Unclear")

    def test_empty_or_none_defaults_to_unclear(self):
        self.assertEqual(_helper._parse_source_verdict(""), "Unclear")
        self.assertEqual(_helper._parse_source_verdict(None), "Unclear")

    def test_garbage_response_defaults_to_unclear(self):
        self.assertEqual(
            _helper._parse_source_verdict("I cannot determine this."), "Unclear"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
