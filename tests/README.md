# Tests

All tests here run fully offline against a small local stub of the
`genlayer` SDK (`genlayer_stub/`) — no GenLayer node, network access,
or real LLM required. They import `contract.py` directly and
monkeypatch `gl.nondet.web.render` / `gl.nondet.exec_prompt` to
simulate specific scenarios deterministically.

## Running

```bash
# everything
python3 -m unittest discover -s tests -p "test_*.py" -v

# a single file
python3 -m unittest tests.test_aggregation -v

# a single test
python3 -m unittest tests.test_aggregation.TestAggregation.test_majority_with_dissent_still_verifies
```

`gltest_integration_example.py` is deliberately excluded from the
`test_*.py` discovery pattern (it needs a live GenLayer Studio/node
and the `gltest` package) — see its own docstring and the main
[README](../README.md#live-genlayer-integration-tests--example-only-not-yet-validated)
for how to run it separately once you have those available.

## Layout

| File | Tests | What it covers |
|---|---|---|
| `test_domain_extraction.py` | 26 | `_extract_domain` / `_registrable_domain`: the four required subdomain-independence cases, multi-part suffix handling (`co.uk`, ...), IPv6 literals, trailing DNS dots, length limits, invalid schemes; plus (v2.8) `_normalize_domain_declaration` for `expected_domains` entries |
| `test_content_classification.py` | 11 | `_classify_content`: all five malformed-content checks (length, word count, printable ratio, alpha ratio, diversity) plus boilerplate detection, and explicit "must NOT false-positive" cases |
| `test_aggregation.py` | 15 | `_aggregate`: every branch of the final-verdict decision rule, including majority-with-dissent, duplicate/low-credibility exclusion; plus (v2.8) staleness and source-authority exclusion, and missing-key backward compatibility |
| `test_parser.py` | 8 | `_parse_source_verdict`: exact/case-insensitive matching, multi-line responses, whitespace tolerance, substring false-positive guard |
| `test_prompt_and_consensus.py` | 12 | `_build_prompt` guardrail presence (injection, quoted claims, opinions, syndication, speculation, v2.8 freshness) and `EQUIVALENCE_PRINCIPLE` schema consistency |
| `test_input_validation.py` | 9 | `submit_claim`'s pre-fetch validation: source-count bounds, length limits, denylist-only rejection, `gl.vm.UserError` typing |
| `test_end_to_end.py` | 22 | Full `submit_claim` → `get_claim` pipeline: verification, refutation, disputes, duplicates, failures, adversarial sources; plus (v2.8) `expected_domains` policy enforcement and freshness/staleness gating |
| `test_storage.py` | 8 | `get_claim` / `get_verdict` / `total_claims`, and multi-claim storage isolation |
| **Total** | **111** | |

## Why split like this instead of one file

Each file corresponds to one deterministic unit of the contract (one
helper function, or the full pipeline) rather than being organized by
"type of bug" or "which review round found it." A reviewer who wants
to check "is domain extraction actually correct?" can read exactly
one ~200-line file and see every case, instead of searching a single
1000+ line file. `tests/_bootstrap.py` centralizes the offline-stub
wiring so each file only has one import line to trust, rather than
duplicating (and risking drift in) the same setup code eight times.

## Coverage checklist

Every item explicitly requested for this project maps to a test file:

- ✅ valid claims → `test_end_to_end.py`
- ✅ insufficient sources → `test_input_validation.py`
- ✅ duplicate domains (incl. subdomains) → `test_domain_extraction.py`, `test_end_to_end.py`
- ✅ malformed URLs → `test_domain_extraction.py`
- ✅ inaccessible URLs → `test_end_to_end.py`
- ✅ timeout handling → `test_end_to_end.py`
- ✅ empty content → `test_content_classification.py`, `test_end_to_end.py`
- ✅ malformed content → `test_content_classification.py`, `test_end_to_end.py`
- ✅ low-credibility domains → `test_aggregation.py`, `test_end_to_end.py`
- ✅ aggregation logic → `test_aggregation.py`
- ✅ parser behavior → `test_parser.py`
- ✅ registrable-domain extraction → `test_domain_extraction.py`
- ✅ content classification → `test_content_classification.py`
- ✅ boundary values → length limits in `test_domain_extraction.py` / `test_input_validation.py`, threshold edges in `test_content_classification.py`
- ✅ storage persistence → `test_storage.py`
- ✅ source-authority policy (`expected_domains`) → `test_domain_extraction.py`, `test_aggregation.py`, `test_end_to_end.py`
- ✅ freshness / staleness gating → `test_prompt_and_consensus.py`, `test_aggregation.py`, `test_end_to_end.py`
