"""
⚠️ EXAMPLE / SKETCH ONLY — NOT YET VALIDATED AGAINST A LIVE GENLAYER
ENVIRONMENT. Do not treat this file as a verified, passing test
suite until it has actually been run.

Live GenLayer integration test sketch for TruthBeacon v2, using the
official `gltest` framework (see: https://pypi.org/project/genlayer-test/).

Unlike tests/test_contract_logic.py (which runs fully offline against
a stub SDK and IS actually executed and passing - 87/87 tests - as
part of this submission), THIS file has never been run. There is no
GenLayer Studio or local node available in the environment this
contract was developed in, so these tests could not be executed or
confirmed to pass. The exact `gltest` API surface used below
(`get_contract_factory(...)`, `factory.deploy(...)`, the
`mock_web_responses=` / `mock_llm_responses=` keyword arguments, and
the `MockedLLMResponse` substring-matching behavior) is based on
published `gltest` documentation but has not been confirmed against
a real installed version of the package, and may need small
adjustments (parameter names, mock dict shape, etc.) before it will
actually run.

Use this file as a starting point for writing real integration tests
once you have a GenLayer Studio/testnet available - validate it
there, fix whatever doesn't match your `gltest` version, and only
then treat it as a trustworthy part of the test suite.

It is included to document how the five scenarios required by the
review (successful verification, conflicting evidence, duplicate
domains, failed fetches, malicious sources), plus one additional
upfront-rejection scenario added during critical review, map onto
GenLayer's own mocked-web / mocked-LLM test tooling, using `gltest`'s
Mock Web Response and Mocked LLM Response systems so these tests would
be deterministic and not depend on real websites being up, once
validated.

Run with a GenLayer Studio instance running:
    pip install genlayer-test --break-system-packages
    gltest test tests/gltest_integration_example.py

This file is NOT executed by the offline unit test suite and is NOT
part of the "87 tests passing" claim made elsewhere in this project.
"""

import json

import pytest
from gltest import get_contract_factory
from gltest.types import MockedLLMResponse, MockedWebResponse


CLAIM = "The Eiffel Tower is located in Paris, France."

GOOD_URLS = [
    "https://reuters.example/eiffel-tower",
    "https://apnews.example/eiffel-tower",
    "https://britannica.example/eiffel-tower",
]


@pytest.fixture
def truth_beacon():
    factory = get_contract_factory("TruthBeacon")
    return factory.deploy(args=[])


def test_successful_verification(truth_beacon):
    """Three independent, agreeing sources -> 'Verified'."""
    mock_web = {
        url: MockedWebResponse(status_code=200, body="The Eiffel Tower stands in Paris, France, near the Seine.")
        for url in GOOD_URLS
    }
    mock_llm: MockedLLMResponse = {"nondet_exec_prompt": {"default": "Supported"}}

    claim_id = truth_beacon.submit_claim(
        args=[CLAIM, GOOD_URLS],
        mock_web_responses=mock_web,
        mock_llm_responses=mock_llm,
    )
    result = json.loads(truth_beacon.get_claim(args=[claim_id]))
    assert result["final_verdict"] == "Verified"
    assert result["independent_domain_count"] == 3


def test_conflicting_evidence(truth_beacon):
    """Independent sources disagree -> 'Disputed'."""
    urls = [
        "https://prosource.example/story",
        "https://consource.example/story",
        "https://neutralsource.example/story",
    ]
    mock_web = {
        urls[0]: MockedWebResponse(status_code=200, body="Evidence strongly confirms the claim."),
        urls[1]: MockedWebResponse(status_code=200, body="Evidence strongly contradicts the claim."),
        urls[2]: MockedWebResponse(status_code=200, body="Evidence is mixed and inconclusive."),
    }
    # gltest's mock LLM system pattern-matches on the constructed user
    # message, so distinct source content routes to distinct verdicts.
    mock_llm: MockedLLMResponse = {
        "nondet_exec_prompt": {
            "confirms the claim": "Supported",
            "contradicts the claim": "NotSupported",
            "mixed and inconclusive": "Unclear",
        }
    }

    claim_id = truth_beacon.submit_claim(
        args=["A contested claim", urls],
        mock_web_responses=mock_web,
        mock_llm_responses=mock_llm,
    )
    result = json.loads(truth_beacon.get_claim(args=[claim_id]))
    assert result["final_verdict"] == "Disputed"


def test_duplicate_domains_not_independent(truth_beacon):
    """Two URLs on the same domain only count as one independent source."""
    urls = [
        "https://news.example/story",
        "https://news.example/story-syndicated",
        "https://other.example/story",
    ]
    mock_web = {u: MockedWebResponse(status_code=200, body="Confirms the claim clearly.") for u in urls}
    mock_llm: MockedLLMResponse = {"nondet_exec_prompt": {"default": "Supported"}}

    claim_id = truth_beacon.submit_claim(
        args=["Some claim", urls],
        mock_web_responses=mock_web,
        mock_llm_responses=mock_llm,
    )
    result = json.loads(truth_beacon.get_claim(args=[claim_id]))
    assert result["duplicate_domain_count"] == 1
    assert result["independent_domain_count"] == 2


def test_failed_fetches_handled_gracefully(truth_beacon):
    """Timeouts / dead links / empty pages degrade to InsufficientEvidence, not a crash."""
    urls = [
        "https://timeout.example/a",
        "https://dead.example/b",
        "https://good.example/c",
    ]
    mock_web = {
        urls[0]: MockedWebResponse(status_code=408, body=""),
        urls[1]: MockedWebResponse(status_code=404, body=""),
        urls[2]: MockedWebResponse(status_code=200, body="Confirms the claim clearly and at length."),
    }
    mock_llm: MockedLLMResponse = {"nondet_exec_prompt": {"default": "Supported"}}

    claim_id = truth_beacon.submit_claim(
        args=["Some claim", urls],
        mock_web_responses=mock_web,
        mock_llm_responses=mock_llm,
    )
    result = json.loads(truth_beacon.get_claim(args=[claim_id]))
    assert result["final_verdict"] == "InsufficientEvidence"
    assert result["failed_source_count"] == 2


def test_malicious_low_credibility_source(truth_beacon):
    """
    A known fake-news domain cannot single-handedly verify a claim,
    even alongside enough real domain diversity to pass pre-flight
    validation.

    NOTE: a submission consisting ONLY of denylisted domains (or with
    fewer than MIN_INDEPENDENT_DOMAINS non-denylisted domains) is now
    rejected by submit_claim's pre-flight check before any fetch/LLM
    cost is spent - see test_all_denylisted_submission_rejected_upfront
    below. This scenario instead demonstrates the case that DOES reach
    the fetch/aggregation stage: two real, non-denylisted domains are
    submitted (satisfying pre-flight validation) alongside a fake-news
    domain, but one of the real domains fails to fetch, leaving only
    one real source successfully resolved - still not enough for
    "Verified", even though the fake-news source also said "Supported".
    """
    urls = [
        "https://theonion.com/story",
        "https://real-outlet-a.example/story",
        "https://real-outlet-b.example/story",
    ]
    mock_web = {
        urls[0]: MockedWebResponse(status_code=200, body="Confirms the claim clearly."),
        urls[1]: MockedWebResponse(status_code=200, body="Confirms the claim clearly."),
        urls[2]: MockedWebResponse(status_code=503, body=""),
    }
    mock_llm: MockedLLMResponse = {"nondet_exec_prompt": {"default": "Supported"}}

    claim_id = truth_beacon.submit_claim(
        args=["An implausible claim", urls],
        mock_web_responses=mock_web,
        mock_llm_responses=mock_llm,
    )
    result = json.loads(truth_beacon.get_claim(args=[claim_id]))
    # Only one real, credible, independent source successfully
    # resolved -> not enough, even with the fake-news source agreeing.
    assert result["final_verdict"] == "InsufficientEvidence"


def test_all_denylisted_submission_rejected_upfront(truth_beacon):
    """
    A submission built ENTIRELY from denylisted domains can
    mathematically never resolve to anything but
    "InsufficientEvidence", so it's rejected at input validation,
    before any fetch/LLM cost is spent on it.
    """
    urls = [
        "https://theonion.com/a",
        "https://clickhole.com/b",
        "https://thebeaverton.com/c",
    ]
    with pytest.raises(Exception):
        truth_beacon.submit_claim(args=["Some claim", urls])
