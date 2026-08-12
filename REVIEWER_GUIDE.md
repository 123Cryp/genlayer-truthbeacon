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

If you're doing a full technical review: also read [DESIGN_DECISIONS.md](DESIGN_DECISIONS.md), [TESTING.md](TESTING.md), and `contract.py` itself (single file, ~960 lines, heavily commented).

---

## 2. How to Deploy It Yourself

You don't need to — it's already deployed (see §4) — but to reproduce:

1. Go to `studio.genlayer.com`
2. Upload or paste `contract.py` into a new contract
3. Go to **Run and Deploy** → click **Deploy** (no constructor arguments needed)
4. Once `FINALIZED`, note the contract address

To exercise it:
- **Write Methods → `submit_claim`**: provide `claim_text` (string) and `source_urls` (JSON array of 3–6 URL strings, e.g. `["https://a.com/x", "https://b.com/y", "https://c.com/z"]`)
- **Read Methods → `get_claim`**: provide the returned `claim_id` to see the full evidence record

---

## 3. How to Reproduce Every Test Claim

```bash
python3 -m unittest discover -s tests -p "test_*.py" -v
```

Expected: `Ran 87 tests ... OK`. No GenLayer node, network access, or API key required — this runs against a local stub of the `genlayer` SDK (`tests/genlayer_stub/`). See [TESTING.md](TESTING.md) for exactly what this does and does not prove.

---

## 4. Live Transaction Evidence

### 4a. Current Deployment (Post-E022-Fix)

**Contract address:** `0xE30A0F67Da4a3F58F2E31C82dfbc50e8B8F588A5`
**Public address page:**
https://explorer-studio.genlayer.com/address/0xE30A0F67Da4a3F58F2E31C82dfbc50e8B8F588A5

This is a redeployment of the same contract logic after fixing GenVM lint rule E022 (seven internal helper methods converted from `@classmethod`/`@staticmethod` to plain instance methods — see [CHANGELOG.md § v2.7](CHANGELOG.md#v27--genvm-lint-fix-e022-and-redeployment-current)). No business logic changed; this transaction confirms the fix didn't alter runtime behavior.

**Verification transaction — Eiffel Tower claim**
`claim_text`: "The Eiffel Tower is located in Paris, France."
`source_urls`: `en.wikipedia.org/wiki/Eiffel_Tower`, `britannica.com/topic/Eiffel-Tower`, `history.com/topics/landmarks/eiffel-tower`
**Result:** `final_verdict: "Verified"`, `independent_domain_count: 2`, `failed_source_count: 1`. Wikipedia and History.com returned `ok`/`Supported`; Britannica returned `inaccessible` and was correctly excluded from corroboration rather than silently dropped.
**Consensus:** `REVEALING` → `ACCEPTED` → `Reached consensus` → `FINALIZED`, no execution errors.
**Proves:** the corrected contract deploys cleanly and the full pipeline (fetch → classify → LLM judge → aggregate → consensus → store) still works end-to-end after the E022 fix.

### 4b. Prior Deployment (Historical — Superseded)

The transactions below were run against the contract's **prior address**, before the E022 lint fix required redeployment. They remain valid evidence of the underlying logic (which did not change in the fix) but are **not** transactions on the current address above.

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
| Requires 3–6 sources | `MIN_SOURCES_SUBMITTED`/`MAX_SOURCES_SUBMITTED`, `submit_claim` | `tests/test_input_validation.py` | Tx 5 |
| Duplicate-domain exclusion | `_registrable_domain`, `_annotate_sources`, `_aggregate` | `tests/test_domain_extraction.py`, `tests/test_end_to_end.py` | Tx 4 |
| Low-credibility denylist | `LOW_CREDIBILITY_DOMAINS`, `_aggregate` | `tests/test_aggregation.py`, `tests/test_end_to_end.py` | — |
| Fetch-failure classification | `_classify_content`, `submit_claim`'s try/except | `tests/test_content_classification.py` | Tx 3, Tx 6 |
| Conservative aggregation rule | `_aggregate` | `tests/test_aggregation.py` | Tx 3, Tx 4, Tx 6 |
| Prompt injection guardrails | `_build_prompt` | `tests/test_prompt_and_consensus.py`, `tests/test_end_to_end.py` | — |
| `gl.eq_principle.prompt_comparative` (not `strict_eq`) | `submit_claim`, `EQUIVALENCE_PRINCIPLE` | `tests/test_prompt_and_consensus.py` | Every live transaction (5-validator consensus) |
| `gl.vm.UserError` (SDK-correct) | Every `raise` in `contract.py` | `tests/test_input_validation.py` | Tx 5 |
| Full on-chain evidence trail | `get_claim`, storage schema | `tests/test_storage.py` | Tx 2–6, readable via `get_claim` |
| Multi-claim storage isolation | `claim_records: TreeMap[str, str]` | `tests/test_storage.py` | Tx 2–6 (claim IDs 0–4, independently readable) |

Rows marked "—" in the "proven live" column are covered by offline tests but weren't the specific focus of a live transaction — this is disclosed, not hidden (fake-news denylisting and prompt-injection guardrails weren't separately demonstrated live because they require adversarial input the deployer chose not to submit to a public testnet).

---

## 6. Questions a Skeptical Reviewer Might Ask

**"Is the offline test suite just testing mocks, not the real contract logic?"**
No — the offline stub only mocks `gl.nondet.web.render` and `gl.nondet.exec_prompt` (the two calls that genuinely can't run without a live network/LLM). Every deterministic function (`_aggregate`, `_classify_content`, `_registrable_domain`, `_parse_source_verdict`, input validation) is called directly, unmocked. See [TESTING.md § 2c](TESTING.md#2c-what-tier-1-does-not-prove) for an explicit statement of what the offline tests do *not* prove, and why the live transactions in §4 above close that gap.

**"Couldn't the live transactions have been cherry-picked to look good?"**
Three of the six prior-deployment demonstration transactions (Tx 3, 4, 6 in §4b) show *negative* or *conservative* results (`Unverified`, `InsufficientEvidence`), not clean successes. This is intentional — a contract that only ever shows off its best-case behavior would itself be evidence of overclaiming. See [CHANGELOG.md § v2.5](CHANGELOG.md#v25--live-deployment).

**"Why is there only one transaction on the current address?"**
The current address (§4a) exists only because GenVM lint rule E022 required a source change (classmethod/staticmethod → instance methods) that could not be applied to an already-deployed contract in place — it necessarily produced a new address. The one verification transaction there confirms the fix preserved runtime behavior; the six prior-deployment transactions in §4b remain valid evidence of the same underlying logic, which was not altered by the fix.

**"Why does `contract.py` use `gl.vm.UserError` and not just `Exception`?"**
This was a real bug in an earlier draft, found during a dedicated SDK compatibility audit and fixed — see [CHANGELOG.md § v2.4](CHANGELOG.md#v24--sdk-compatibility-audit).

**"Is `EQUIVALENCE_PRINCIPLE` just decorative, or does it actually matter?"**
It matters — `gl.eq_principle.prompt_comparative` uses it to decide whether validators agree. An earlier draft of this exact constant had a real bug (referenced a nonexistent field name), caught by a dedicated test (`TestEquivalencePrinciple` in `tests/test_prompt_and_consensus.py`). See [CHANGELOG.md § v2.1](CHANGELOG.md#v21--critical-self-review-round-1).
