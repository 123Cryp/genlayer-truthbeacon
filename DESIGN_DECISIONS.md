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

**Trade-offs:** None significant — this is a strict improvement in both cost and clarity, since deterministic logic is also the easiest to unit-test exhaustively (69 of the 87 offline tests exercise pure deterministic functions with zero mocking required).

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
