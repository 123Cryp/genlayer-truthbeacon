"""
Tests for deterministic fetched-content classification
(TruthBeacon._classify_content).

Covers all five malformed-content checks (length, word count,
printable ratio, alphabetic ratio, word diversity) plus the
short-boilerplate check, including explicit "must NOT be penalized"
cases for legitimate short/long text so the heuristic's false-positive
rate is pinned down, not just its true-positive rate.
"""

import unittest

from tests._bootstrap import TruthBeacon, make_contract

# Shared helper instance used to call former classmethod/staticmethod
# helpers, which are now plain instance methods (GenVM lint rule E022
# requires self as the first parameter on every gl.Contract method).
_helper = make_contract()


class TestContentClassification(unittest.TestCase):
    """
    Pure function: fetched content -> fetch_status.

    Covers each of the (now five) deterministic malformed-content
    checks individually, so a future change to one check's threshold
    can't silently break another check without a test noticing.
    """

    def test_ok_content(self):
        status, usable = _helper._classify_content(
            "This is a perfectly normal, long enough news article body. " * 3
        )
        self.assertEqual(status, "ok")
        self.assertTrue(usable)

    def test_empty_content(self):
        status, usable = _helper._classify_content("   \n\t  ")
        self.assertEqual(status, "empty")
        self.assertFalse(usable)

    def test_none_content(self):
        status, usable = _helper._classify_content(None)
        self.assertEqual(status, "empty")
        self.assertFalse(usable)

    def test_too_short_is_malformed(self):
        status, usable = _helper._classify_content("hi")
        self.assertEqual(status, "malformed")
        self.assertFalse(usable)

    def test_low_word_count_despite_length_is_malformed(self):
        # Long in characters, but has no whitespace at all - so it's
        # really just one giant "word", not an article.
        status, usable = _helper._classify_content("a" * 200)
        self.assertEqual(status, "malformed")
        self.assertFalse(usable)

    def test_low_printable_ratio_is_malformed(self):
        garbage = "\x01\x02\x03\x04" * 20
        status, usable = _helper._classify_content(garbage)
        self.assertEqual(status, "malformed")
        self.assertFalse(usable)

    def test_low_alpha_ratio_is_malformed(self):
        # Printable, has "words" by whitespace-splitting, but is
        # almost entirely digits - i.e. a data dump, not prose.
        numeric_spam = " ".join(
            ["12345", "67890", "11111", "22222", "33333", "44444", "55555", "66666"]
        )
        status, usable = _helper._classify_content(numeric_spam)
        self.assertEqual(status, "malformed")
        self.assertFalse(usable)

    def test_repeated_garbage_low_diversity_is_malformed(self):
        # 30 words, but only one distinct word - the classic
        # "keyword-stuffed spam page" pattern.
        spam = " ".join(["spam"] * 30)
        status, usable = _helper._classify_content(spam)
        self.assertEqual(status, "malformed")
        self.assertFalse(usable)

    def test_short_legitimate_article_is_not_penalized_for_diversity(self):
        # Short, real prose naturally repeats common words ("the",
        # "a") - it must NOT be penalized by the diversity check,
        # which only applies once there are enough words for
        # repetition to be a meaningful signal.
        article = (
            "The mayor announced a new policy today. Officials said "
            "it would take effect next month across the city."
        )
        status, usable = _helper._classify_content(article)
        self.assertEqual(status, "ok")
        self.assertTrue(usable)

    def test_boilerplate_bot_wall_page_is_malformed(self):
        page = (
            "Access denied. You do not have permission to access this "
            "resource on this server today."
        )
        status, usable = _helper._classify_content(page)
        self.assertEqual(status, "malformed")
        self.assertFalse(usable)

    def test_long_article_mentioning_boilerplate_phrase_is_not_penalized(self):
        # The boilerplate check only fires on SHORT pages; a long,
        # substantive article that happens to quote or reference one
        # of the marker phrases (e.g. reporting ABOUT bot-wall pages)
        # should not be misclassified.
        long_article = (
            "Officials described how the outage began. " * 3
            + "The affected site briefly displayed an access denied "
            "message before service was restored later that day. "
            + "Officials described how the outage began. " * 5
        )
        status, usable = _helper._classify_content(long_article)
        self.assertEqual(status, "ok")
        self.assertTrue(usable)


if __name__ == "__main__":
    unittest.main(verbosity=2)
