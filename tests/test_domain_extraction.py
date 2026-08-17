"""
Tests for approximate registrable-domain extraction
(TruthBeacon._extract_domain / _registrable_domain).

Covers the four required subdomain-independence cases (example.com /
www.example.com / news.example.com / mirror.example.com), multi-part
suffix handling (co.uk, ...) and its documented over-merge
limitation, and the trailing-DNS-root-dot / IPv6-bracket-literal edge
cases found and fixed during critical review. See README
"Domain-independence limitations" for the full trade-off discussion.
"""

import unittest

from tests._bootstrap import TruthBeacon, make_contract

# Shared helper instance used to call former classmethod/staticmethod
# helpers, which are now plain instance methods (GenVM lint rule E022
# requires self as the first parameter on every gl.Contract method).
_helper = make_contract()


class TestDomainExtraction(unittest.TestCase):
    """
    Pure function: URL -> approximate registrable domain.

    As of this revision, _extract_domain no longer returns the raw
    hostname - it returns an approximate "registrable domain" (a
    lightweight, PSL-free stand-in for eTLD+1), specifically so that
    subdomains of the same publisher can no longer be submitted as
    fake independent sources. See README "Domain-independence
    limitations" for the full trade-off discussion.
    """

    def test_basic_https(self):
        self.assertEqual(
            _helper._extract_domain("https://www.example.com/page?x=1"),
            "example.com",
        )

    def test_strips_port_and_userinfo(self):
        self.assertEqual(
            _helper._extract_domain("https://user:pass@www.example.com:8443/x"),
            "example.com",
        )

    def test_invalid_scheme_returns_empty(self):
        self.assertEqual(_helper._extract_domain("ftp://example.com"), "")
        self.assertEqual(_helper._extract_domain("not a url"), "")

    # --- The four required cases: example.com / www / news / mirror ---
    #
    # All four are DELIBERATELY considered the SAME domain by this
    # contract: they share the registrable domain "example.com", and
    # in practice a publisher (or an adversary impersonating one)
    # controls all of its own subdomains equally. Treating them as
    # independent would let a single actor submit
    # "news.example.com" + "mirror.example.com" + "example.com" as
    # "3 independent sources" when they are really just one.

    def test_bare_domain(self):
        self.assertEqual(
            _helper._extract_domain("https://example.com/a"), "example.com"
        )

    def test_www_subdomain_same_as_bare_domain(self):
        self.assertEqual(
            _helper._extract_domain("https://www.example.com/a"),
            "example.com",
        )

    def test_news_subdomain_same_as_bare_domain(self):
        self.assertEqual(
            _helper._extract_domain("https://news.example.com/a"),
            "example.com",
        )

    def test_mirror_subdomain_same_as_bare_domain(self):
        self.assertEqual(
            _helper._extract_domain("https://mirror.example.com/a"),
            "example.com",
        )

    def test_all_four_example_variants_are_identical(self):
        variants = [
            "https://example.com/a",
            "https://www.example.com/a",
            "https://news.example.com/a",
            "https://mirror.example.com/a",
        ]
        domains = {_helper._extract_domain(u) for u in variants}
        self.assertEqual(domains, {"example.com"})

    # --- Genuinely different publishers must stay independent ---

    def test_different_publishers_are_different_domains(self):
        a = _helper._extract_domain("https://bbc.com/story")
        b = _helper._extract_domain("https://cnn.com/story")
        self.assertNotEqual(a, b)

    # --- Multi-part suffix handling (co.uk, com.au, ...) ---

    def test_known_multi_part_suffix_keeps_distinct_publishers_independent(self):
        # "co.uk" alone would be far too broad a bucket (it would
        # merge every UK company domain together); KNOWN_MULTI_PART_
        # SUFFIXES exists specifically so bbc.co.uk and itv.co.uk stay
        # distinct, independent domains.
        a = _helper._extract_domain("https://www.bbc.co.uk/news")
        b = _helper._extract_domain("https://www.itv.co.uk/news")
        self.assertEqual(a, "bbc.co.uk")
        self.assertEqual(b, "itv.co.uk")
        self.assertNotEqual(a, b)

    def test_known_multi_part_suffix_merges_own_subdomains(self):
        # Subdomains of the SAME co.uk publisher still correctly
        # collapse to one domain, same as the plain .com case above.
        a = _helper._extract_domain("https://news.bbc.co.uk/story")
        b = _helper._extract_domain("https://sport.bbc.co.uk/story")
        self.assertEqual(a, b)
        self.assertEqual(a, "bbc.co.uk")

    def test_known_limitation_unrecognized_multi_part_suffix_may_overmerge(self):
        # DOCUMENTED, DELIBERATE LIMITATION: "gov.xx" is not in our
        # small KNOWN_MULTI_PART_SUFFIXES list, so two otherwise
        # unrelated agencies under an unrecognized multi-part suffix
        # are (incorrectly) treated as the same domain by this naive
        # heuristic. This test exists so the limitation is pinned
        # down and visible, not silently discovered later. See
        # README "Domain-independence limitations".
        a = _helper._extract_domain("https://agency-one.gov.xx/page")
        b = _helper._extract_domain("https://agency-two.gov.xx/page")
        self.assertEqual(a, b)
        self.assertEqual(a, "gov.xx")

    def test_ip_address_host_is_returned_unmodified(self):
        self.assertEqual(
            _helper._extract_domain("http://192.168.0.1/status"),
            "192.168.0.1",
        )

    def test_single_label_host_is_returned_unmodified(self):
        self.assertEqual(
            _helper._extract_domain("http://localhost/status"), "localhost"
        )

    def test_trailing_dns_root_dot_is_normalized(self):
        # "example.com." (trailing dot) is valid DNS syntax equivalent
        # to "example.com" - without normalizing it, naive label
        # splitting would incorrectly reduce this to "com.".
        self.assertEqual(
            _helper._extract_domain("https://example.com./page"),
            "example.com",
        )

    def test_ipv6_bracket_literal_is_handled_without_corruption(self):
        # IPv6 literals use bracket notation with an optional port,
        # e.g. "[::1]:8080". A naive split on ":" would mutilate the
        # address itself; this must extract the address cleanly
        # instead of producing a nonsense one-character domain.
        self.assertEqual(
            _helper._extract_domain("https://[::1]:8080/path"), "::1"
        )

    def test_malformed_ipv6_bracket_literal_is_invalid(self):
        # An unterminated bracket (no closing "]") is treated as an
        # invalid URL rather than guessed at.
        self.assertEqual(_helper._extract_domain("https://[::1/path"), "")

    def test_url_exceeding_max_length_is_invalid(self):
        too_long = "https://example.com/" + ("a" * TruthBeacon.MAX_URL_CHARS)
        self.assertEqual(_helper._extract_domain(too_long), "")


class TestNormalizeDomainDeclaration(unittest.TestCase):
    """
    Pure function: a caller-declared `expected_domains` entry (see
    submit_claim, v2.8) -> the same approximate registrable-domain
    form _extract_domain computes for actual source URLs.

    This is what lets submit_claim compare "the domain a fetched
    source actually resolved to" against "the domain the claim
    creator pre-declared as authorized" using one consistent
    representation on both sides.
    """

    def test_bare_domain_is_normalized(self):
        self.assertEqual(
            _helper._normalize_domain_declaration("reuters.com"), "reuters.com"
        )

    def test_bare_domain_with_www_normalizes_same_as_without(self):
        self.assertEqual(
            _helper._normalize_domain_declaration("www.reuters.com"),
            "reuters.com",
        )

    def test_full_url_normalizes_to_same_domain_as_bare_form(self):
        self.assertEqual(
            _helper._normalize_domain_declaration("https://reuters.com/article"),
            "reuters.com",
        )

    def test_uppercase_and_whitespace_are_normalized(self):
        self.assertEqual(
            _helper._normalize_domain_declaration("  Reuters.COM  "),
            "reuters.com",
        )

    def test_multi_part_suffix_domain_is_normalized_consistently(self):
        # Delegates to _extract_domain, so it inherits the same
        # KNOWN_MULTI_PART_SUFFIXES handling as real source URLs.
        self.assertEqual(
            _helper._normalize_domain_declaration("bbc.co.uk"), "bbc.co.uk"
        )

    def test_empty_string_is_invalid(self):
        self.assertEqual(_helper._normalize_domain_declaration(""), "")
        self.assertEqual(_helper._normalize_domain_declaration("   "), "")

    def test_overlong_entry_is_invalid(self):
        too_long = "a" * (TruthBeacon.MAX_URL_CHARS + 1) + ".com"
        self.assertEqual(_helper._normalize_domain_declaration(too_long), "")

    def test_unparseable_entry_is_invalid(self):
        self.assertEqual(_helper._normalize_domain_declaration("ftp://x.com"), "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
