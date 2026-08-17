# Reviewer Guide

This document is written for a GenLayer judge or reviewer. It tells you what to read first, how to deploy and reproduce the contract yourself, and — most importantly — exactly where to look to independently verify every claim made in this repository.

---

## 1. What to Read First

If you have 5 minutes: [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md).

If you have 15 minutes, in this order:
1. This document's [§4 Live Transaction Evidence](#4-live-transaction-evidence) below — see it working before reading how it works
2. [README.md](README.md) — interface and aggregation rule
3. [ARCHITECTURE.md](ARCHITECTURE.md) — how it's built
4. [SECURITY.md](SECURITY.md) — what it defends against

If you're doing a full technical review: also read [DESIGN_DECISIONS.md](DESIGN_DECISIONS.md), [TESTING.md](TESTING.md), and `contract.py` itself (single file, ~1200 lines, heavily commented).

---

## 2. How to Deploy It Yourself

You don't need to — it's already deployed (see §4) — but to reproduce:

1. Go to `studio.genlayer.com`
2. Upload or paste `contract.py` into a new contract
3. Go to **Run and Deploy** → click **Deploy** (no constructor arguments needed)
4. Once `FINALIZED`, note the contract address

To exercise it:
- **Write Methods → `submit_claim`**: provide `claim_text` (string), `source_urls` (JSON array of 3–6 URL strings, e.g. `["https://a.com/x", "https://b.com/y", "https://c.com/z"]`), and optionally `expected_domains` (JSON array of bare domains or URLs, e.g. `["a.com", "b.com"]` — leave as `[]` to skip the source-authority policy)
- **Read Methods → `get_claim`**: provide the returned `claim_id` to see the full evidence record

---

## 3. How to Reproduce Every Test Claim

```bash
python3 -m unittest discover -s tests -p "test_*.py" -v
```

Expected: `Ran 111 tests ... OK`. No GenLayer node, network access, or API key required — this runs against a local stub of the `genlayer` SDK (`tests/genlayer_stub/`). See [TESTING.md](TESTING.md) for exactly what this does and does not prove.

---

## 4. Live Transaction Evidence

### 4a. Current Deployment (v2.8 — Source-Authority Policy + Freshness Signal)

**Contract address:** `0x93F0F657a008FC99a41149E444AA37a604A14580`
**Public address page:**
https://explorer-studio.genlayer.com/address/0x93F0F657a008FC99a41149E444AA37a604A14580

This redeployment adds the `expected_domains` source-authority policy and the `Current`/`Stale`/`Undated` freshness signal (see [CHANGELOG.md § v2.8](CHANGELOG.md#v28--source-authority-policy--freshness-signal-current)). Both new mechanisms are exercised by dedicated live transactions below, not just offline tests.

**Verification transaction 1 — `expected_domains` source-authority policy**
`0x1891eb4645f426774c0301e3e9c7069d6fc253747381ed7672d7ef710afb5296` — FINALIZED
`claim_text`: "The Eiffel Tower is located in Paris, France."
`source_urls`: `en.wikipedia.org/wiki/Eiffel_Tower`, `britannica.com/topic/Eiffel-Tower`, `history.com/topics/landmarks/eiffel-tower`
`expected_domains`: `["wikipedia.org", "britannica.com"]` — `history.com` deliberately omitted
**Result:** `final_verdict: "InsufficientEvidence"`, `unauthorized_domain_count: 1`. `history.com` was fetched and judged `Supported` exactly like the other sources, but was correctly flagged `is_authorized_domain: false` and excluded from corroboration because it wasn't in the declared `expected_domains`. `britannica.com` independently failed to fetch (`inaccessible`, a real network failure, unrelated to the authorization check). With only 1 authorized+reachable source left, the contract correctly refused to declare `Verified`.
**Proves:** the source-authority policy is locked in at submission time and genuinely gates corroboration eligibility — a source doesn't get to count just because it returned a favorable verdict. Implemented in: `_normalize_domain_declaration`, `_annotate_sources`, `_aggregate`, `submit_claim` in `contract.py`. Documented in [SECURITY.md § 10](SECURITY.md#10-source-authority-policy-gaming-v28).

**Verification transaction 2 — freshness / staleness signal**
`0x760cdaa2fefec430d5b2896643b546255d500c9028c9bad01d759e4826e98a54` — FINALIZED
`claim_text`: "The James Webb Space Telescope was launched in December 2021."
`source_urls`: a live Wikipedia article, a NASA page, and a 2018 Wayback Machine snapshot of the pre-launch Wikipedia article
`expected_domains`: `[]` (no source-authority policy — isolating the freshness mechanism)
**Result:** `final_verdict: "InsufficientEvidence"`, `stale_source_count: 1`. The live Wikipedia source came back `freshness: "Current"`. The 2018 archived snapshot — describing JWST as a future, not-yet-launched project — was correctly judged `freshness: "Stale"`, flagged `is_stale: true`, and excluded from corroboration, independently of the fact that its `verdict` also came back `NotSupported`. NASA's page independently failed to fetch (`inaccessible`).
**Proves:** freshness is judged from actual page content (not merely inferred from the verdict) and genuinely gates corroboration eligibility, exactly like a duplicate or denylisted domain would. Implemented in: `_build_prompt`, `_parse_freshness_label`, `_aggregate` in `contract.py`. Documented in [SECURITY.md § 11](SECURITY.md#11-freshness-gaming--stale-content-corroboration-v28).

**Consensus note (both transactions):** both reached `ACCEPTED` → `FINALIZED` via `gl.eq_principle.prompt_comparative`. Transaction 2's consensus history shows several validators marked `Disagree` against the leader's exact proposal before the round still finalized — this is expected `prompt_comparative` behavior (validators judge *equivalence* under `EQUIVALENCE_PRINCIPLE`, not byte-identical text) and not an execution error.

### 4b. Prior Deployment (Post-E022-Fix, Historical — Superseded by v2.8)

**Contract address:** `0xE30A0F67Da4a3F58F2E31C82dfbc50e8B8F588A5`
**Public address page:**
https://explorer-studio.genlayer.com/address/0xE30A0F67Da4a3F58F2E31C82dfbc50e8B8F588A5

This was a redeployment of the same base contract logic after fixing GenVM lint rule E022 (seven internal helper methods converted from `@classmethod`/`@staticmethod` to plain instance methods — see [CHANGELOG.md § v2.7](CHANGELOG.md#v27--genvm-lint-fix-e022-and-redeployment)). No business logic changed; the transaction below confirms the fix didn't alter runtime behavior. It predates the v2.8 source-authority/freshness policy — see §4a above for that.

**Verification transaction — Eiffel Tower claim**
`claim_text`: "The Eiffel Tower is located in Paris, France."
`source_urls`: `en.wikipedia.org/wiki/Eiffel_Tower`, `britannica.com/topic/Eiffel-Tower`, `history.com/topics/landmarks/eiffel-tower`
**Result:** `final_verdict: "Verified"`, `independent_domain_count: 2`, `failed_source_count: 1`. Wikipedia and History.com returned `ok`/`Supported`; Britannica returned `inaccessible` and was correctly excluded from corroboration rather than silently dropped.
**Consensus:** `REVEALING` → `ACCEPTED` → `Reached consensus` → `FINALIZED`, no execution errors.
**Proves:** the corrected contract deploys cleanly and the full pipeline (fetch → classify → LLM judge → aggregate → consensus → store) still works end-to-end after the E022 fix.

### 4c. Original Prior Deployment (Historical — Superseded)

The transactions below were run against the contract's **original** address, before the E022 lint fix required redeployment. They remain valid evidence of the underlying base logic (which did not change in the fix) but are **not** transactions on either address above.

**Prior contract address:** `0xF7275bA620A2a405905f8d93356012166753a62A`
**Public address page:**
https://explorer-studio.genlayer.com/address/0xF7275bA620A2a405905f8d93356012166753a62A

### Transaction 1 — Deploy
`0x89f90b71d5e9b563a1136c562930daad128c038240dc9b072d3eea279ccfddf1`
Status: FINALIZED / SUCCESS. 5/5 validators (running Sonnet, Kimi, GPT-OSS, Gemini, GPT-5) Agree.
**Proves:** the contract deploys cleanly on real GenVM infrastructure with no constructor arguments.

### Transaction 2 — Clean successful verification
`0xfd19c79a2ab086d63e31e743c9d4383c5d40e8931f04077a0db5dba1b29b2940`
`claim_text`: "The Apollo 11 mission landed on the Moon in 1969."
`source_urls`: Wikipedia, NASA, History.com (3 distinct domains)
**Result:** `final_verdict: "Verified"`, `independent_domain_count: 3`, `failed_source_count: 0`, all three sources `Supported`.
**Proves:** the full pipeline (fetch → classify → LLM judge → aggregate → consensus → store) works end-to-end and reaches a clean positive result when evidence genuinely supports it. Implemented in: `submit_claim`, `_annotate_sources`, `_classify_content`, `_build_prompt`, `_parse_source_verdict`, `_aggregate` in `contract.py`.

### Transaction 3 — Conservative behavior under incomplete evidence
`0xb784c266da6a176a7f6c00f8b039960dbc1924393e201942bd1c8ad4dbd40f34`
`claim_text`: "Neil Armstrong was the first person to walk on the Moon."
`source_urls`: Britannica, History.com, NASA
**Result:** `final_verdict: "Unverified"` — britannica.com was `inaccessible` (real fetch failure), history.com returned `Unclear`, only nasa.gov returned `Supported`. Since `independent_total >= 2` but `support < 2`, the aggregation rule (`_aggregate` in `contract.py`) correctly refused to claim `Verified`.
**Proves:** the contract does not default to a confident answer when evidence is thin, even for an undisputed fact — direct, live evidence against the original rejection's concern about unearned trust. Implements the "InsufficientEvidence unless ≥2 independent sources agree" rule described in [README.md § Aggregation Logic](README.md#aggregation-logic) and justified in [DESIGN_DECISIONS.md § 6](DESIGN_DECISIONS.md#6-why-conservative-aggregation).

### Transaction 4 — Live duplicate-domain detection
`0x6b3bdd448a030c32d1783b0c1f8ccfb534f35866409b7ea06c067f95eac7b274`
`claim_text`: "The Eiffel Tower is located in Paris, France."
`source_urls`: `en.wikipedia.org/wiki/Eiffel_Tower`, `en.wikipedia.org/wiki/Paris`, `britannica.com`
**Result:** `final_verdict: "InsufficientEvidence"`. Both Wikipedia URLs returned `ok`/`Supported`, but the second was flagged `is_duplicate_domain: true` (same registrable domain) and excluded from corroboration; britannica.com was `inaccessible`. `independent_domain_count: 1`, `duplicate_domain_count: 1`.
**Proves:** the exact mechanism the original rejection called out ("no way to distinguish 3 independent newspapers from 3 copies of the same blog post") is fixed and verified live, not just in mocked tests. Implemented in: `_registrable_domain`, `_annotate_sources` in `contract.py`. Documented in [SECURITY.md § 4](SECURITY.md#4-duplicate-domain--sybil-style-source-abuse).

### Transaction 5 — Deterministic input-validation rejection
`0xe9338d2c44c262bab60155b3fd02f43b0906196d9cc90fed3c73df0a028e7595`
`claim_text`: "Test claim", `source_urls`: only 2 URLs (below the minimum of 3)
**Result:** ERROR. All 5 validators (GPT-5, Sonnet, Gemini, Mistral, Qwen) independently produced the byte-identical rollback message: `"[rollback] At least 3 candidate source URLs are required for independent corroboration (got 2)."`
**Proves:** deterministic pre-flight validation (plain Python, no `gl.nondet.*` calls) runs identically across every validator regardless of which LLM they use, and rejects invalid input before any fetch/LLM cost is spent. Implemented in: `submit_claim`'s validation block (before the `nondet()` closure) in `contract.py`. Documented in [DESIGN_DECISIONS.md § 7](DESIGN_DECISIONS.md#7-why-deterministic-preprocessing-before-any-non-deterministic-step).

### Transaction 6 — Second real-world fetch-failure instance
`0x1ce1f1b9e6470b526aec50039d1081c909cb825858a3a37621d78f54ceb57c93`
`claim_text`: "Water boils at 100 degrees Celsius at sea level atmospheric pressure."
`source_urls`: Wikipedia, Britannica, USGS
**Result:** `final_verdict: "InsufficientEvidence"` — britannica.com and usgs.gov both `inaccessible`, only Wikipedia succeeded.
**Proves:** graceful fetch-failure handling is not a one-off — it recurred independently in a separate transaction with different URLs, and the contract handled it identically both times.

---

## 5. Claim → Implementation → Evidence Map

| Claim in documentation | Where implemented | Where tested | Where proven live |
|---|---|---|---|
| Requires 3–6 sources | `MIN_SOURCES_SUBMITTED`/`MAX_SOURCES_SUBMITTED`, `submit_claim` | `tests/test_input_validation.py` | Tx 5 (§4c) |
| Duplicate-domain exclusion | `_registrable_domain`, `_annotate_sources`, `_aggregate` | `tests/test_domain_extraction.py`, `tests/test_end_to_end.py` | Tx 4 (§4c) |
| Low-credibility denylist | `LOW_CREDIBILITY_DOMAINS`, `_aggregate` | `tests/test_aggregation.py`, `tests/test_end_to_end.py` | — |
| Fetch-failure classification | `_classify_content`, `submit_claim`'s try/except | `tests/test_content_classification.py` | Tx 3, Tx 6 (§4c) |
| Conservative aggregation rule | `_aggregate` | `tests/test_aggregation.py` | Tx 3, Tx 4, Tx 6 (§4c) |
| Prompt injection guardrails | `_build_prompt` | `tests/test_prompt_and_consensus.py`, `tests/test_end_to_end.py` | — |
| `gl.eq_principle.prompt_comparative` (not `strict_eq`) | `submit_claim`, `EQUIVALENCE_PRINCIPLE` | `tests/test_prompt_and_consensus.py` | Every live transaction (multi-validator consensus) |
| `gl.vm.UserError` (SDK-correct) | Every `raise` in `contract.py` | `tests/test_input_validation.py` | Tx 5 (§4c) |
| Full on-chain evidence trail | `get_claim`, storage schema | `tests/test_storage.py` | Tx 2–6 (§4c), readable via `get_claim` |
| Multi-claim storage isolation | `claim_records: TreeMap[str, str]` | `tests/test_storage.py` | Tx 2–6 (§4c, claim IDs 0–4, independently readable) |
| **Source-authority policy (`expected_domains`), v2.8** | `_normalize_domain_declaration`, `_annotate_sources`, `_aggregate`, `submit_claim` | `tests/test_domain_extraction.py`, `tests/test_aggregation.py`, `tests/test_end_to_end.py` | **Tx 1, §4a** |
| **Freshness signal (`Current`/`Stale`/`Undated`), v2.8** | `_build_prompt`, `_parse_freshness_label`, `_aggregate` | `tests/test_prompt_and_consensus.py`, `tests/test_aggregation.py`, `tests/test_end_to_end.py` | **Tx 2, §4a** |

Rows marked "—" in the "proven live" column are covered by offline tests but weren't the specific focus of a live transaction — this is disclosed, not hidden (fake-news denylisting and prompt-injection guardrails weren't separately demonstrated live because they require adversarial input the deployer chose not to submit to a public testnet).

---

## 6. Questions a Skeptical Reviewer Might Ask

**"Is the offline test suite just testing mocks, not the real contract logic?"**
No — the offline stub only mocks `gl.nondet.web.render` and `gl.nondet.exec_prompt` (the two calls that genuinely can't run without a live network/LLM). Every deterministic function (`_aggregate`, `_classify_content`, `_registrable_domain`, `_parse_source_verdict`, `_parse_freshness_label`, `_normalize_domain_declaration`, input validation) is called directly, unmocked. See [TESTING.md § 2c](TESTING.md#2c-what-tier-1-does-not-prove) for an explicit statement of what the offline tests do *not* prove, and why the live transactions in §4 above close that gap.

**"Couldn't the live transactions have been cherry-picked to look good?"**
Three of the six §4c demonstration transactions show *negative* or *conservative* results (`Unverified`, `InsufficientEvidence`), not clean successes. Both §4a v2.8 transactions also resolve to `InsufficientEvidence` — the source-authority and freshness exclusions were specifically constructed to trigger, and the live result shows the excluded source genuinely being excluded rather than silently counted anyway. This is intentional — a contract that only ever shows off its best-case behavior would itself be evidence of overclaiming. See [CHANGELOG.md § v2.5](CHANGELOG.md#v25--live-deployment).

**"Why does the contract address keep changing?"**
GenLayer Intelligent Contract source is fixed at its address — any source change requires redeployment to a new address. This has happened twice: once for the E022 lint fix (§4b, no behavior change, one verification transaction), and once for the v2.8 source-authority + freshness policy (§4a, an actual behavior addition, two dedicated verification transactions). The §4c transactions remain valid evidence of the base logic, which neither redeployment altered.

**"Why does `contract.py` use `gl.vm.UserError` and not just `Exception`?"**
This was a real bug in an earlier draft, found during a dedicated SDK compatibility audit and fixed — see [CHANGELOG.md § v2.4](CHANGELOG.md#v24--sdk-compatibility-audit).

**"Is `EQUIVALENCE_PRINCIPLE` just decorative, or does it actually matter?"**
It matters — `gl.eq_principle.prompt_comparative` uses it to decide whether validators agree. An earlier draft of this exact constant had a real bug (referenced a nonexistent field name), caught by a dedicated test (`TestEquivalencePrinciple` in `tests/test_prompt_and_consensus.py`). See [CHANGELOG.md § v2.1](CHANGELOG.md#v21--critical-self-review-round-1). The v2.8 live transaction 2 (§4a) shows the comparator actively at work: several validators' raw outputs were marked `Disagree` against the leader's exact proposal before the round still finalized — expected behavior for a *comparative*, not exact-match, principle.
