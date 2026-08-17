# Design Decisions

Every significant design choice in TruthBeacon v2, in the format: **Problem → Chosen Solution → Alternative Considered → Trade-offs**.

---

## 1. Why `TreeMap` for Storage

**Problem:** The contract needs to persist an unbounded, growing number of claims, each identified by a unique ID, queryable individually.

**Chosen solution:** `claim_records: TreeMap[str, str]`, keyed by sequential claim ID (`"0"`, `"1"`, `"2"`, ...).

**Alternative considered:** `DynArray` (append-only list) with claim ID as index. Rejected because `TreeMap` gives O(log n) lookup by key without needing to iterate, and using string keys keeps the ID scheme decoupled from raw array indices if the storage model ever needs to change.

**Trade-offs:** `TreeMap` requires converting the integer claim counter to a string key on every read/write (minor overhead, no correctness cost). No ability to efficiently enumerate "all claims" without knowing IDs in advance — acceptable since `total_claims()` combined with sequential IDs (`"0"` through `total_claims()-1`) already provides enumeration.

---

## 2. Why JSON Storage (One Blob Per Claim) Instead of Multiple Fields

**Problem:** Each claim needs to store multiple related pieces of data: claim text, final verdict, aggregate stats, and a full per-source evidence array (URL, domain, flags, fetch status, verdict — for every submitted source).

**Chosen solution:** Serialize everything into one JSON string per claim, stored under one `TreeMap[str, str]`.

**Alternative considered:** Multiple parallel `TreeMap`s (one for claim text, one for verdicts, one for evidence, etc.), all keyed by the same claim ID. Rejected because GenLayer's storage type system does not natively support nested structures like "a list of dicts" as a persisted type — modeling the per-source evidence array would require either a fixed-width scheme (breaking the variable 3–6 source count) or several more parallel TreeMaps keyed by `f"{claim_id}:{source_index}"`, which introduces a real risk of the parallel structures drifting out of sync (e.g., a claim's verdict map missing an entry that its evidence map has).

**Trade-offs:** Every read/write does a full JSON encode/decode of the claim's data, not a targeted field update. For a fact-checking contract where claims are written once and read whole, this is the right trade — a single source of truth is more auditable than four TreeMaps that must always agree.

---

## 3. Why `prompt_comparative`, Not `strict_eq`

**Problem:** The contract's non-deterministic closure (`nondet()`) performs live web fetches and LLM calls per source. Its result must be validated for consensus across validators.

**Chosen solution:** `gl.eq_principle.prompt_comparative(nondet, principle=EQUIVALENCE_PRINCIPLE)`.

**Alternative considered:** `gl.eq_principle.strict_eq(nondet)` — used in an earlier draft of this contract. Rejected (and actively fixed) because GenLayer's own documentation states that `strict_eq` must never be used for LLM-derived output: independent LLM calls are not guaranteed to produce byte-identical text even when every validator reaches the same substantive conclusion, so exact-match consensus can fail for reasons unrelated to correctness.

**Trade-offs:** `prompt_comparative` introduces its own non-determinism (the comparator LLM's judgment of "equivalence"), which is why `EQUIVALENCE_PRINCIPLE` is written as a precise, field-by-field rule rather than a vague instruction — this keeps the comparator's job as close to deterministic categorical-equality-checking as possible. See [ARCHITECTURE.md](ARCHITECTURE.md#4-why-prompt_comparative-not-strict_eq) for the full mechanism.

---

## 4. Why Bounded Source Count (3–6)

**Problem:** Too few sources defeats the purpose of corroboration (back to the single-source problem this contract was redesigned to fix). Too many sources is expensive and risks consensus reliability (more independent fetch+LLM steps per round = more chances for validator disagreement).

**Chosen solution:** `MIN_SOURCES_SUBMITTED = 3`, `MAX_SOURCES_SUBMITTED = 6`.

**Alternative considered:** No upper bound, or a much higher one (e.g., 20). Rejected because gas/LLM cost scales linearly with source count, and each additional source is one more chance for a transient fetch failure or LLM disagreement to complicate consensus in a single round.

**Trade-offs:** A genuinely well-corroborated claim with 10 excellent sources can only submit 6 at a time (a caller could submit a second claim to cover more, at the cost of a second consensus round and separate claim ID). This is judged an acceptable trade for cost predictability and consensus reliability.

---

## 5. Why Fixed Vocabularies

**Problem:** Every value returned from the non-deterministic closure must be judgeable by the `prompt_comparative` comparator for equivalence across validators. Open-ended text (raw model explanations, exact page content) makes this judgment ambiguous and unreliable.

**Chosen solution:** Three small, closed vocabularies — `SOURCE_VERDICTS = ("Supported", "NotSupported", "Unclear", "NoEvidence")`, `FETCH_STATUSES = ("ok", "empty", "timeout", "inaccessible", "malformed")`, `FINAL_VERDICTS = ("Verified", "Refuted", "Disputed", "Unverified", "InsufficientEvidence")`. Any LLM output outside the vocabulary is deterministically mapped to `Unclear` by `_parse_source_verdict`, never passed through raw.

**Alternative considered:** Free-form LLM explanations stored alongside each verdict, for richer auditability. Rejected because free text is exactly what breaks comparator-based equivalence judgments, and because storing large amounts of LLM-generated prose on-chain is expensive and not necessary for the contract's stated purpose (a verdict plus structured provenance, not a narrative).

**Trade-offs:** Less nuance than a full explanation would give — a source judged "Unclear" doesn't record *why* it was unclear. This is deliberate: `url`, `domain`, and `fetch_status` already provide enough structured provenance for a human to investigate the source directly if the one-word verdict isn't enough.

---

## 6. Why Conservative Aggregation

**Problem:** How should the contract combine several per-source verdicts (some `Supported`, some `NotSupported`, some `Unclear`, some failed) into one final answer, without ever overclaiming confidence?

**Chosen solution:** `_aggregate`'s decision rule (see [README.md](README.md#aggregation-logic-made-unambiguous) for the exact table) requires **at least 2 independent, credible, successfully-fetched sources** to agree before reaching `Verified` or `Refuted`; anything short of that resolves to `InsufficientEvidence`, `Disputed`, or `Unverified` — never a confident-sounding guess.

**Alternative considered:** A simple majority-vote rule with no minimum absolute count (e.g., 1 support vs. 0 oppose = "Verified"). Rejected because a single source, however unanimous among the sources that happened to succeed, is exactly the failure mode the original rejection identified.

**Trade-offs:** This conservatism was directly observed live: a Studio test with an undisputed historical fact (Neil Armstrong on the Moon) returned `Unverified`, not `Verified`, because only one of three sources both fetched successfully and gave an unambiguous "Supported" — see [REVIEWER_GUIDE.md](REVIEWER_GUIDE.md). This is treated as a feature, not a bug: the contract would rather under-claim than over-claim.

---

## 7. Why Deterministic Preprocessing (Before Any Non-Deterministic Step)

**Problem:** Input validation, domain extraction, and duplicate/denylist detection could technically happen inside the non-deterministic closure alongside the fetches. Where should the line be drawn?

**Chosen solution:** Everything that can be computed purely from the caller-supplied `claim_text` and `source_urls` — length limits, source-count bounds, domain normalization, duplicate detection, denylist checks — happens in plain Python *before* `nondet()` is ever called, and can reject the transaction outright via `gl.vm.UserError`.

**Alternative considered:** Doing all of this inside the non-deterministic closure, so a single code path handles everything. Rejected because it would mean every validator spends real fetch/LLM cost on a submission that could have been rejected for free (e.g., all-denylisted-domain submissions, or fewer than 3 sources) — verified live: an invalid-input transaction with only 2 sources was rejected by all 5 validators with an identical message, before any web fetch happened (see [REVIEWER_GUIDE.md](REVIEWER_GUIDE.md)).

**Trade-offs:** None significant — this is a strict improvement in both cost and clarity, since deterministic logic is also the easiest to unit-test exhaustively (the large majority of the 111 offline tests exercise pure deterministic functions with zero mocking required — see [tests/README.md](tests/README.md) for the file-by-file breakdown). The same reasoning is why v2.8's `expected_domains` validation (§ 10 below) is also deterministic pre-flight logic, not something deferred into `nondet()`.

---

## 8. Why an Approximate Registrable Domain, Not a Full Public Suffix List

**Problem:** Deduplicating sources by domain requires knowing that `news.example.com` and `www.example.com` are the same publisher, while `bbc.co.uk` and `itv.co.uk` are not (even though both end in `co.uk`).

**Chosen solution:** `_registrable_domain` uses the last two labels of a hostname as the domain identity, with a small hardcoded set (`KNOWN_MULTI_PART_SUFFIXES`) of common multi-part suffixes (`co.uk`, `com.au`, etc.) where the last *three* labels are kept instead.

**Alternative considered:** A full Public Suffix List (PSL) implementation. Rejected because a real PSL has thousands of entries and changes over time — bundling it would either require network access from consensus-critical code (breaking determinism) or freezing a potentially-stale copy indefinitely, with no clean update path inside a deterministic contract.

**Trade-offs:** Explicitly disclosed and tested: an unrecognized multi-part suffix (e.g. a fictitious `gov.xx`) will incorrectly merge two unrelated publishers under that suffix (`test_known_limitation_unrecognized_multi_part_suffix_may_overmerge`). This biases toward *under-counting* independence (too strict) rather than *over-counting* it (too lenient) — the safer direction for a corroboration mechanism.

---

## 9. Why a Static Denylist Instead of a Reputation Score

**Problem:** Some domains are known to be unreliable (satire sites, fabricated-news domains). How should the contract account for this without depending on a live, mutable, external reputation service?

**Chosen solution:** `LOW_CREDIBILITY_DOMAINS` — a small, explicit, hardcoded `frozenset` baked into the contract source.

**Alternative considered:** A live reputation API or oracle. Rejected for the same determinism reason as the PSL: an external, potentially-changing data source cannot be safely queried from inside consensus-critical code without risking validators seeing different data at different times.

**Trade-offs:** The list is small, illustrative, and requires a contract upgrade to extend — acceptable for an educational reference implementation, explicitly flagged as a production gap. See [ROADMAP.md](ROADMAP.md) for the governance-registry alternative.

---

## 10. Why `expected_domains` Is an Optional Allowlist, Not a Trust-Tier Score (v2.8)

**Problem:** The steward's review suggested a "stronger source-authority... policy so distinct domains provide more assurance of genuine independent corroboration" — but `submit_claim` is a single atomic transaction (fetch and judgment happen in the same call as submission), so there's no separate "resolution" step to protect against in the literal sense of a two-phase propose/resolve design. What's the right shape for a source-authority mechanism here?

**Chosen solution:** An optional `expected_domains: list[str]` parameter, checked and normalized entirely in deterministic pre-flight code (alongside `_annotate_sources`, per § 7 above) before any fetch happens, and gating `_aggregate` eligibility via a new `is_authorized_domain` flag — architecturally identical in shape to the existing `LOW_CREDIBILITY_DOMAINS` gate, just caller-declared per-claim instead of contract-wide and hardcoded.

**Alternative considered:** A numeric/tiered "trust score" per domain (e.g. `min_trust_tier: "any" | "standard" | "high"` mapped against a contract-maintained tiered domain database). Rejected for this iteration: it would require the contract to maintain and periodically extend an opinionated, hardcoded tier assignment for arbitrary domains — the same static-list-maintenance burden already disclosed as a known limitation for `LOW_CREDIBILITY_DOMAINS` (see [SECURITY.md § 8](SECURITY.md#8-known-limitations-not-fixed-by-design)), but now for an open-ended "which domains are high-trust" judgment that's considerably more subjective and contestable than "which domains are known bad actors." An explicit, per-claim, creator-declared allowlist sidesteps that subjectivity: the contract doesn't have to adjudicate whose domains are "trustworthy" in the abstract, only whether the *submitted* sources match what the *claim creator themselves* committed to up front.

**Trade-offs:** `expected_domains` is caller-declared, not independently vetted (see [SECURITY.md § 10](SECURITY.md#10-source-authority-policy-gaming-v28) for the full residual-risk discussion) — a creator could declare a low-quality domain as "expected." What this mechanism guarantees is narrower but still valuable: the *policy itself* is locked in atomically with the claim, auditable on-chain (`expected_domains` in `get_claim`'s persisted record), and cannot be redefined or reinterpreted after the fact to make a weak set of sources look pre-approved. A tiered trust-score system remains a natural, larger follow-up — see [ROADMAP.md](ROADMAP.md).

---

## 11. Why Freshness Is a Second Line in the Same Prompt, Not a Second LLM Call (v2.8)

**Problem:** Classifying whether a fetched source presents current/recent information, versus stale or undated content, requires the same kind of contextual judgment as the existing `Supported`/`NotSupported`/`Unclear` verdict — but it's a genuinely separate question (a source can be "Supported" and "Stale" at the same time). How should this second judgment be obtained without doubling the LLM cost of every `submit_claim` call, or destabilizing the existing fixed-vocabulary consensus design?

**Chosen solution:** Extend the existing single `gl.nondet.exec_prompt` call per source to request exactly two lines back — verdict, then freshness — parsed independently by two separate deterministic parsers (`_parse_source_verdict`, unchanged; `_parse_freshness_label`, new). `_parse_source_verdict` already scans every line of the response looking for a vocabulary match rather than only the first line, so adding a second line to the response format required zero changes to the existing verdict-parsing logic — only an additive prompt instruction and a new parser for the new line.

**Alternative considered:** A second, independent `gl.nondet.exec_prompt` call dedicated to freshness. Rejected: it would double the number of LLM calls (and therefore roughly double cost and latency) for every source, for a judgment that the model can make from the exact same page content it's already reading to produce the verdict — there's no information-locality reason to split it into a separate call.

**Trade-offs:** The prompt is now instructing the model to produce a stricter two-line format instead of one word, which is a slightly larger ask of model compliance; this is mitigated the same way the rest of this contract mitigates off-vocabulary model output — both `_parse_source_verdict` and `_parse_freshness_label` default safely (`Unclear` / `Undated` respectively) for anything that doesn't parse, rather than raising or guessing. `_parse_freshness_label`'s unparseable-default is deliberately `Undated` (the conservative, excluded-from-corroboration option) rather than `Current`, consistent with this contract's general "when unsure, don't count it" philosophy (see § 6 above) — see `test_missing_freshness_key_defaults_to_not_stale` in `tests/test_aggregation.py` for why that default is *also* safe for records that never went through this prompt at all (backward compatibility, not the same code path).
