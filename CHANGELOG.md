# Changelog

All notable changes to TruthBeacon are documented here, in chronological order.

---

## v1 — Original Contract (Rejected)

Single-source fact-checking: accepted exactly one caller-selected URL and asked validators whether that page supported a claim.

**Reviewer feedback (verbatim):**
> "The contract checks whether one caller-selected page supports a claim, but it cannot establish that the source or claim is trustworthy. Add provenance checks or independent corroboration, retain auditable evidence, and test failure and adversarial-source cases."

**Identified gaps:**
- No independent corroboration — a single page could be fabricated, mirrored, or simply wrong
- No way to distinguish "3 independent newspapers agree" from "3 copies of the same blog post"
- Fetch failures (dead links, timeouts, empty pages) were not distinguished from genuine "NotSupported" verdicts
- No provenance metadata recorded — nobody could audit *why* a verdict was reached
- No adversarial-source or failure-case testing

---

## v2 — Corroboration Redesign

Complete redesign addressing every clause of the rejection. See the full mapping in [README.md § Reviewer Feedback Addressed](README.md#reviewer-feedback-addressed).

**Added:**
- Multi-source requirement: `MIN_SOURCES_SUBMITTED = 3`, `MAX_SOURCES_SUBMITTED = 6`
- Registrable-domain-based duplicate detection (`_registrable_domain`, `_annotate_sources`)
- Low-credibility domain denylist, excluded from corroboration
- Full per-source provenance persisted on-chain (URL, domain, duplicate/denylist flags, fetch status, verdict)
- Explicit fetch-failure classification: `timeout`, `inaccessible`, `empty`, `malformed`, distinct from `ok`
- Conservative aggregation rule requiring ≥2 independent, credible sources for `Verified`/`Refuted`
- Hardened LLM prompt guarding against manipulated-page prompt injection
- Initial offline test suite

**Architecture at this stage:** used `gl.eq_principle.strict_eq()` for the fetch+LLM consensus pipeline.

---

## v2.1 — Critical Self-Review Round 1

A dedicated adversarial self-review pass, acting as a strict reviewer trying to reject the submission.

| Issue | Severity | Fix |
|---|---|---|
| Used `gl.eq_principle.strict_eq()` to wrap multiple LLM calls — GenLayer's own docs say this must never be done for LLM-derived output | **Critical** | Switched to `gl.eq_principle.prompt_comparative(nondet, principle=EQUIVALENCE_PRINCIPLE)` |
| `EQUIVALENCE_PRINCIPLE` referenced a `'sources'` field that didn't exist in `nondet()`'s actual return value | High | Corrected to `'records'`; added a regression test |
| No prompt-injection guardrail for `claim_text` itself (only fetched source content) | **Critical** | Added a parallel guardrail; a malicious caller could otherwise hijack every verdict via the claim text |
| User-facing errors raised bare `Exception` instead of GenLayer's documented error type | High | Replaced throughout; tested |
| Submissions built entirely from denylisted domains passed pre-flight checks and wasted a fetch+LLM round | High | Pre-flight check now excludes low-credibility domains from the distinct-domain count |
| LLM verdict parsing only checked the response's first line | High | Rewrote to scan all lines with whole-line exact matching |
| No length caps on `claim_text` or URLs | Medium | Added `MAX_CLAIM_TEXT_CHARS`, `MAX_URL_CHARS` |
| Trailing DNS root dot (`example.com.`) mis-parsed to `com.` | Medium | Fixed in `_extract_domain`; tested |
| IPv6 bracket-literal hosts (`[::1]:8080`) collapsed to `[` | Medium | Fixed; tested |

Test count: 58 → 81.

---

## v2.2 — Critical Self-Review Round 2 (Fresh-Eyes Pass)

| Issue | Severity | Fix |
|---|---|---|
| `_parse_source_verdict` required an exact match against `"NotSupported"` with no internal space | Medium | Collapse internal whitespace before comparison |
| `EQUIVALENCE_PRINCIPLE` didn't explicitly list all three stat-count fields | Low | Made explicit |
| `"Refuted"` had no end-to-end test through the full pipeline, only through `_aggregate` directly | Medium | Added `test_successful_refutation_three_independent_disagreeing_sources` |
| Failed-fetch test didn't assert `verdict: "NoEvidence"` explicitly | Low | Added assertions |
| The unexecuted `gltest` example's malicious-source scenario no longer matched actual pre-flight behavior | Medium | Rewrote the scenario; fixed stale test-count references |

Test count: 81 → 87.

---

## v2.3 — Repository Reorganization

Non-behavioral improvements for reviewer experience:
- Split the monolithic 1100+ line test file into 8 focused files by function under test, with a shared `tests/_bootstrap.py`
- Fixed a redundant double-`__init__` call in the test helper
- Renamed the unexecuted `gltest` example so it's excluded from `unittest discover`'s default pattern by construction, not by convention
- Restored an accidentally-deleted `## Architecture` heading; added a Mermaid diagram
- Fixed stale file-path references across README/tests-README

---

## v2.4 — SDK Compatibility Audit

A dedicated pass verifying every GenLayer API call against current official documentation.

**Finding:** `gl.UserError` (bare, top-level) does not exist in the current GenLayer SDK. The current documented path — confirmed via the official `WizardOfCoin` reference example and the SDK changelog — is `gl.vm.UserError`.

**Fix:** All 7 occurrences in `contract.py` corrected to `gl.vm.UserError`, plus the test stub and dependent tests updated to match.

**Confirmed correct (no change needed):** `gl.public.write`/`gl.public.view`, `TreeMap`, `u256`, `gl.nondet.web.render(url, mode="text")`, `gl.nondet.exec_prompt(prompt, response_format="text")`, `gl.eq_principle.prompt_comparative(fn, principle)`, the `from genlayer import *` import style, and the `Depends` dependency-pin header.

---

## v2.5 — Live Deployment

First real deployment to GenLayer Studio, replacing offline-only confidence with observed on-chain behavior.

**Contract address:** `0xF7275bA620A2a405905f8d93356012166753a62A`

- Deploy transaction: successful, 5/5 validators agree
- Live test 1: clean `Verified` result (3 sources, all reachable, all agree)
- Live test 2: `Unverified` result — conservative behavior confirmed live when evidence was incomplete, even for an undisputed fact
- Live test 3: `InsufficientEvidence` with live duplicate-domain detection (two Wikipedia URLs, one correctly excluded)
- Live test 4: input-validation rejection — all 5 validators (5 different LLMs) independently produced byte-identical rejection messages
- Live test 5: a second real-world instance of graceful fetch-failure handling

Full transaction details: [REVIEWER_GUIDE.md](REVIEWER_GUIDE.md).

---

## v2.6 — Full Documentation Suite

Added the complete professional documentation set: `ARCHITECTURE.md`, `SECURITY.md`, `DESIGN_DECISIONS.md`, `TESTING.md`, `CONTRIBUTING.md`, `CHANGELOG.md` (this file), `ROADMAP.md`, `RELEASE_NOTES_v2.md`, `SUBMISSION_CHECKLIST.md`, `REVIEWER_GUIDE.md`, `PROJECT_OVERVIEW.md`. README restructured to reduce duplication and act as a navigation hub. No code changes in this round — documentation only.

---

## v2.7 — GenVM Lint Fix (E022) and Redeployment

**Reviewer feedback addressed:** "The submitted and deployed contract source matches, but the current source fails GenVM lint with E022 diagnostics on seven helper methods because they do not use self as the first parameter."

**Finding:** GenVM lint rule E022 requires every method on a `gl.Contract` subclass to be a plain instance method with `self` as the first parameter. Seven internal helper methods were declared as `@classmethod`/`@staticmethod`, which GenVM's linter does not accept even for pure, stateless logic.

**Fix:** All seven helpers converted to plain instance methods:
- `_extract_domain` (was `@classmethod`)
- `_registrable_domain` (was `@classmethod`)
- `_annotate_sources` (was `@classmethod`)
- `_classify_content` (was `@classmethod`)
- `_aggregate` (was `@classmethod`)
- `_parse_source_verdict` (was `@classmethod`)
- `_build_prompt` (was `@staticmethod`)

For each, the decorator was removed, the first parameter became `self`, and every internal `cls` reference (class-constant access and cross-calls between helpers) was updated to `self`. No business logic, thresholds, prompts, aggregation rules, or public API (`submit_claim`, `get_claim`, `get_verdict`, `total_claims`) changed. The offline test suite (`tests/`) was updated to call these helpers on a contract instance instead of the class, with zero reduction in coverage — still 87/87 passing.

**Redeployment:** Because the deployed source must match the submitted source, the corrected `contract.py` was redeployed to GenLayer Studio at a new address (the previous address's contract carried the pre-fix source and could not be edited in place):

**New contract address:** `0xE30A0F67Da4a3F58F2E31C82dfbc50e8B8F588A5`

A live `submit_claim` transaction on this new deployment reached a `Verified` verdict from 2 independent corroborating sources (Wikipedia, History.com) on the Eiffel Tower claim, with a third source (Britannica) correctly recorded as `inaccessible` rather than silently ignored. Consensus was reached and finalized with no execution errors, confirming the E022 fix did not alter runtime behavior.

The six transactions recorded against the prior (pre-fix) address in [REVIEWER_GUIDE.md § 4](REVIEWER_GUIDE.md#4-live-transaction-evidence) remain as historical evidence of the same underlying logic under the old address; they are labeled there as prior-deployment evidence, not evidence for the current address.

---

## v2.8 — Source-Authority Policy & Freshness Signal (Current)

**Steward feedback addressed** (left on the Accepted v2.7 submission): "TruthBeacon is a substantive reusable fact-checking contract: it fetches multiple sources inside consensus, handles failed or malformed pages, binds the resulting verdict and evidence categories across validators, and stores an auditable record. A valuable next improvement would be a stronger source-authority and freshness policy so distinct domains provide more assurance of genuine independent corroboration."

**Added:**
- **Source-authority policy** — new optional `expected_domains: list[str]` parameter on `submit_claim`. Normalized and validated in deterministic pre-flight code (new `_normalize_domain_declaration` helper, delegating to `_extract_domain`), before any source is fetched. Gates corroboration eligibility via a new `is_authorized_domain` flag on every source record, computed by `_annotate_sources`. When omitted (default `[]`), every domain is authorized — identical to pre-v2.8 behavior. Persisted on-chain as part of the claim record for auditability.
- **Freshness signal** — the per-source LLM prompt (`_build_prompt`) now requests a second, independent judgment line: `Current` / `Stale` / `Undated`, in addition to the existing verdict line. New `_parse_freshness_label` parses it (mirroring `_parse_source_verdict`'s all-lines scanning approach), defaulting safely to `Undated` for unparseable output. Gates corroboration eligibility via a new `is_stale` flag, exactly like `is_duplicate_domain`/`is_low_credibility` already do.
- Two new top-level corroboration stats, persisted and returned by `get_claim`: `stale_source_count`, `unauthorized_domain_count`.
- New per-source record fields: `is_authorized_domain`, `freshness`, `is_stale`.
- `EQUIVALENCE_PRINCIPLE` extended to check the new `freshness` per-record field and the two new stat fields, following the existing pattern exactly.
- 24 new offline tests across `test_domain_extraction.py` (new `TestNormalizeDomainDeclaration` class), `test_aggregation.py` (staleness/authorization gating, missing-key backward compatibility), `test_prompt_and_consensus.py` (freshness guardrail presence, updated schema-field check), and `test_end_to_end.py` (`expected_domains` enforcement, freshness gating, `NotApplicable` freshness on failed fetches, all exercised through the full `submit_claim` → `get_claim` pipeline).

**Backward compatibility (verified, not just claimed):**
- `_aggregate` reads both new flags via `.get(key, safe_default)` — `is_stale` defaults to `False`, `is_authorized_domain` defaults to `True` — so any record dict built before v2.8 (including every pre-existing test fixture) is unaffected. Covered by `test_missing_freshness_key_defaults_to_not_stale` and `test_missing_authorized_key_defaults_to_authorized`.
- `submit_claim` without `expected_domains` behaves identically to pre-v2.8: `expected_domains` defaults to `[]`, and every domain is authorized. Covered by `test_omitting_expected_domains_is_fully_backward_compatible`.
- All pre-existing mocked-LLM-response test fixtures in `test_end_to_end.py` and `test_storage.py` were updated to include an explicit `"Current"` freshness line, preserving every previously-asserted scenario and outcome exactly (the two-line prompt/response format is new; the scenarios and their expected verdicts are not).
- GenVM lint rule E022 respected throughout: `_normalize_domain_declaration` and `_parse_freshness_label` are plain instance methods with `self` as the first parameter, like every other helper since v2.7 — no new `@classmethod`/`@staticmethod` was introduced.

**Not changed:** `LOW_CREDIBILITY_DOMAINS` denylist logic, duplicate-domain detection, prompt-injection guardrails, `MIN_SOURCES_SUBMITTED`/`MAX_SOURCES_SUBMITTED`/`MIN_INDEPENDENT_DOMAINS` bounds, the aggregation decision table's support/oppose thresholds, and the public method signatures of `get_claim`, `get_verdict`, `total_claims` (all unchanged).

Test count: 87 → 111.

**Deployment status:** **deployed and exercised live.** Redeployed to a new address, `0x93F0F657a008FC99a41149E444AA37a604A14580` (source changes require redeployment; see [README.md § Live Deployment](README.md#live-deployment) for the full detail):
- Tx `0x1891eb4645f426774c0301e3e9c7069d6fc253747381ed7672d7ef710afb5296` (FINALIZED) — a claim submitted with `expected_domains` restricting corroboration to 2 of 3 submitted domains; the third source was fetched, judged `Supported`, and correctly excluded from the count (`unauthorized_domain_count: 1`).
- Tx `0x760cdaa2fefec430d5b2896643b546255d500c9028c9bad01d759e4826e98a54` (FINALIZED) — a claim submitted with a 2018 Wayback Machine snapshot as one of three sources; that source was correctly judged `freshness: "Stale"` and excluded from corroboration (`stale_source_count: 1`), independent of its verdict.

Both transactions reached multi-validator consensus via `gl.eq_principle.prompt_comparative` (validator-level `Agree`/`Disagree` marks on individual raw outputs are expected `prompt_comparative` behavior, not errors — see README).
