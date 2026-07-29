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

## v2.6 — Full Documentation Suite (Current)

Added the complete professional documentation set: `ARCHITECTURE.md`, `SECURITY.md`, `DESIGN_DECISIONS.md`, `TESTING.md`, `CONTRIBUTING.md`, `CHANGELOG.md` (this file), `ROADMAP.md`, `RELEASE_NOTES_v2.md`, `SUBMISSION_CHECKLIST.md`, `REVIEWER_GUIDE.md`, `PROJECT_OVERVIEW.md`. README restructured to reduce duplication and act as a navigation hub. No code changes in this round — documentation only.
