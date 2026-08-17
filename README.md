# TruthBeacon v2 — Corroborated AI Fact-Checking on GenLayer

TruthBeacon is a GenLayer Intelligent Contract for decentralized fact-checking. Anyone submits a claim together with candidate source URLs; GenLayer's validators independently fetch and judge each source, and reach Optimistic Democracy consensus on one deterministic final verdict, stored permanently on-chain with a full, auditable evidence trail.

This is a from-scratch redesign of a previously **rejected** version of this contract (see [Reviewer Feedback Addressed](#reviewer-feedback-addressed) below), and has since been **deployed and tested live on GenLayer Studio** (see [Live Deployment](#live-deployment)).

> **v2.8 update:** this Accepted submission's steward left a specific improvement suggestion — a stronger source-authority and freshness policy (see [Source-Authority & Freshness Policy (v2.8)](#source-authority--freshness-policy-v28) below). That mechanism is implemented, **111/111 offline-tested**, and has now also been **deployed and exercised live** on GenLayer Studio at a new address — see [Live Deployment](#live-deployment) for both transactions.

> **This contract does not determine absolute truth.** It deterministically evaluates whether multiple independent sources corroborate or refute a claim under GenLayer consensus rules. A `Verified` verdict means "enough independent, credible, reachable sources agreed" — not an infallible statement of objective fact.

---

## Documentation Map

| Document | What's in it |
|---|---|
| **README.md** (this file) | Quick start, interface reference, aggregation rule, reviewer feedback mapping |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Component diagram, execution flow, storage/consensus model, why `prompt_comparative` |
| [SECURITY.md](SECURITY.md) | Full threat model — prompt injection, fake news, Sybil domains, fetch failures, known limitations |
| [DESIGN_DECISIONS.md](DESIGN_DECISIONS.md) | Every design choice: problem → solution → alternative considered → trade-offs |
| [TESTING.md](TESTING.md) | Offline tests, the unexecuted integration example, and live deployment evidence tiers |
| [CHANGELOG.md](CHANGELOG.md) | Full version history from the v1 rejection through every review round |
| [ROADMAP.md](ROADMAP.md) | What's intentionally out of scope, and why, for each future direction |
| [CONTRIBUTING.md](CONTRIBUTING.md) | How to contribute, and what not to change casually |
| [REVIEWER_GUIDE.md](REVIEWER_GUIDE.md) | Where every claim in this repo can be independently verified |
| [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md) | 5-minute executive summary |
| [SUBMISSION_CHECKLIST.md](SUBMISSION_CHECKLIST.md) | Pre-submission checklist |
| [RELEASE_NOTES_v2.md](RELEASE_NOTES_v2.md) | What v2 achieved, summarized |
| [tests/README.md](tests/README.md) | Test-file-by-test-file coverage index |

---

## Live Deployment

**Current address (v2.8 — source-authority + freshness policy):** `0x93F0F657a008FC99a41149E444AA37a604A14580`
**Public explorer (all transactions):** https://explorer-studio.genlayer.com/address/0x93F0F657a008FC99a41149E444AA37a604A14580

This is the v2.8 redeployment (see [CHANGELOG.md](CHANGELOG.md)) — a new address, since GenLayer Intelligent Contract source changes require redeployment. Both new v2.8 mechanisms have now been exercised live, not just offline-tested:

**Transaction 1 — `expected_domains` source-authority policy** (tx [`0x1891eb4645f426774c0301e3e9c7069d6fc253747381ed7672d7ef710afb5296`](https://explorer-studio.genlayer.com/tx/0x1891eb4645f426774c0301e3e9c7069d6fc253747381ed7672d7ef710afb5296), **FINALIZED**): `submit_claim("The Eiffel Tower is located in Paris, France.", [wikipedia.org, britannica.com, history.com URLs], expected_domains=["wikipedia.org", "britannica.com"])`. Result (`claim_id "0"`): `history.com` was fetched and judged `Supported` exactly like the other sources, but — because it was not in the declared `expected_domains` — it was correctly flagged `is_authorized_domain: false` and excluded from corroboration (`unauthorized_domain_count: 1`). `britannica.com` independently failed to fetch (`fetch_status: inaccessible`, a real network failure, correctly recorded rather than silently dropped). With only 1 authorized, reachable, credible source left (`independent_domain_count: 1`), the contract correctly returned `final_verdict: InsufficientEvidence` rather than letting the unauthorized source pad the count.

**Transaction 2 — freshness / staleness signal** (tx [`0x760cdaa2fefec430d5b2896643b546255d500c9028c9bad01d759e4826e98a54`](https://explorer-studio.genlayer.com/tx/0x760cdaa2fefec430d5b2896643b546255d500c9028c9bad01d759e4826e98a54), **FINALIZED**): `submit_claim("The James Webb Space Telescope was launched in December 2021.", [a live Wikipedia article, a NASA page, and a 2018 Wayback Machine snapshot of the pre-launch Wikipedia article], expected_domains=[])`. Result (`claim_id "1"`): the live Wikipedia source was judged `Supported` / `freshness: "Current"`. The 2018 archived snapshot — describing JWST as a future, not-yet-launched project — was correctly judged `freshness: "Stale"`, set `is_stale: true`, and excluded from corroboration (`stale_source_count: 1`), independently of the fact that its `verdict` also came back `NotSupported`. The NASA page failed to fetch (`inaccessible`, a real network failure). With only 1 eligible source, the result was again the conservative `final_verdict: InsufficientEvidence`.

Both transactions reached multi-validator consensus (`ACCEPTED` → `FINALIZED`) via `gl.eq_principle.prompt_comparative`, not exact string matching — transaction 2 in particular shows the comparator in action: several validators' raw outputs were marked `Disagree` against the leader's proposal before the round finalized, which is expected `prompt_comparative` behavior (validators judge *equivalence* under `EQUIVALENCE_PRINCIPLE`, not byte-identical output) and not an error.

The prior (pre-v2.8) deployment at `0xE30A0F67Da4a3F58F2E31C82dfbc50e8B8F588A5` remains as historical evidence for the base fetch/aggregate/consensus pipeline (clean `Verified` result, duplicate-domain detection, unanimous rejection, etc.) — full detail in [REVIEWER_GUIDE.md](REVIEWER_GUIDE.md) and [TESTING.md § Tier 3](TESTING.md#4-tier-3--live-deployment-evidence). Those transactions are *not* re-cited as v2.8 evidence; the two transactions above are.

---

## Reviewer Feedback Addressed

> "The contract checks whether one caller-selected page supports a claim, but it cannot establish that the source or claim is trustworthy. Add provenance checks or independent corroboration, retain auditable evidence, and test failure and adversarial-source cases."

| Reviewer comment | How this version addresses it |
|---|---|
| **Checks only one caller-selected page** | `submit_claim` requires 3–6 candidate URLs (`MIN_SOURCES_SUBMITTED`/`MAX_SOURCES_SUBMITTED`). A single-URL submission is not a valid call. |
| **Cannot establish source/claim trustworthiness** | Every source is scored independently by an LLM (`Supported`/`NotSupported`/`Unclear`); a fixed, on-chain denylist (`LOW_CREDIBILITY_DOMAINS`) flags known low-credibility domains, recorded but excluded from corroboration. |
| **Add independent corroboration** | `Verified`/`Refuted` require at least 2 distinct-domain, successfully-fetched, non-denylisted sources to agree, with agreement strictly outnumbering disagreement. See [Aggregation Logic](#aggregation-logic) below. |
| **Add provenance checks** | `_annotate_sources` computes domain, validity, duplicate status, and denylist status for every URL *before* any network access, and this metadata is persisted on-chain in full. |
| **Detect duplicate domains** | Domains are reduced to an approximate registrable form (`_registrable_domain`), so `news.example.com`, `www.example.com`, and `mirror.example.com` are recognized as the same source. Duplicates are recorded but excluded from corroboration. **Verified live** — see [REVIEWER_GUIDE.md](REVIEWER_GUIDE.md). |
| **Retain auditable evidence** | `get_claim(claim_id)` returns the full record: claim text, final verdict, corroboration stats, and a per-source array with URL, domain, provenance flags, fetch status, and verdict for every submitted URL — nothing discarded. |
| **Test failure cases** | Fetch failures are explicitly classified (`timeout`/`inaccessible`/`empty`/`malformed`), never silently treated as evidence. See [TESTING.md](TESTING.md). |
| **Test adversarial-source cases** | Fake-news denylisting, duplicate/Sybil domains, conflicting sources, prompt injection (both claim text and source content), quoted/opinion/speculative content, and garbage pages are all covered. Full mapping in [SECURITY.md](SECURITY.md). |

For the complete history of how this was reached — including two critical self-review rounds and an SDK compatibility audit — see [CHANGELOG.md](CHANGELOG.md).

---

## Source-Authority & Freshness Policy (v2.8)

> Steward's review note on the Accepted submission: "TruthBeacon is a substantive reusable fact-checking contract... A valuable next improvement would be a stronger source-authority and freshness policy so distinct domains provide more assurance of genuine independent corroboration."

| Suggestion | How this version addresses it | Verified by |
|---|---|---|
| **Source-authority policy locked at submission time, not resolution time** | New optional `expected_domains: list[str]` parameter on `submit_claim`. When provided, it's normalized and validated *before* any source is fetched, and only submitted sources whose domain is a member of that pre-declared, submission-time-locked set are eligible to count toward corroboration (`is_authorized_domain` in `_aggregate`). Every source is still fetched and recorded either way — nothing is silently dropped. Left empty (the default), behavior is identical to pre-v2.8: every domain is authorized. | `test_expected_domains_restricts_corroboration_to_declared_set`, `test_expected_domains_accepts_full_urls_as_entries`, `test_omitting_expected_domains_is_fully_backward_compatible`, `test_expected_domains_with_no_matching_sources_is_rejected_upfront` (all in `test_end_to_end.py`); `test_unauthorized_domain_not_counted_as_corroboration`, `test_missing_authorized_key_defaults_to_authorized` (in `test_aggregation.py`) |
| **Freshness signal, gating eligibility like `is_duplicate_domain`/`is_low_credibility`** | The per-source LLM prompt now asks for a second, independent line: a `Current`/`Stale`/`Undated` freshness judgment for the fetched content relative to the claim. `_aggregate` excludes any source flagged `is_stale` (i.e. not `Current`) from corroboration, exactly the same way it already excludes duplicates and denylisted domains. | `test_stale_source_excluded_from_corroboration_end_to_end`, `test_undated_source_excluded_from_corroboration_end_to_end`, `test_failed_fetch_freshness_is_not_applicable` (in `test_end_to_end.py`); `test_stale_source_not_counted_as_corroboration`, `test_undated_source_excluded_same_as_stale`, `test_two_fresh_supports_still_verify_with_a_stale_third`, `test_missing_freshness_key_defaults_to_not_stale` (in `test_aggregation.py`); `test_contains_freshness_guardrail` (in `test_prompt_and_consensus.py`) |

**Backward compatibility:** both new eligibility flags (`is_stale`, `is_authorized_domain`) are read in `_aggregate` with `.get(key, safe_default)` rather than direct indexing, so any pre-existing caller or hand-built record — including every test written before v2.8 — behaves exactly as it did before. `submit_claim` without `expected_domains` is unchanged in every other respect.

**Verified live on GenLayer Studio** (see [Live Deployment](#live-deployment) above for both transactions, addresses, and full result breakdowns) — no longer offline-only.

---

## Architecture (Summary)

```
submit_claim(claim_text, source_urls, expected_domains=[])
        │
        ├─ 1. Deterministic input validation (cheap, fails fast, no gl.* calls)
        │      claim_text ≤ MAX_CLAIM_TEXT_CHARS · 3 ≤ len(source_urls) ≤ 6
        │      ≥ 2 distinct, non-denylisted domains among submitted URLs
        │      expected_domains normalized + validated (v2.8, optional)
        │
        ├─ 2. Deterministic provenance annotation (_annotate_sources)
        │      registrable domain per URL · duplicate flag · denylist flag
        │      is_authorized_domain flag against expected_domains (v2.8)
        │
        ├─ 3. ONE non-deterministic closure (gl.eq_principle.prompt_comparative)
        │      per source: fetch → classify → LLM judge → fixed-vocabulary
        │      verdict + freshness (v2.8) → deterministic aggregation
        │      (now also gated on staleness + authorization) → one final
        │      verdict + stats
        │
        └─ 4. Persist claim + verdict + full evidence trail to on-chain storage
```

Full component diagrams, sequence diagrams, and the "why `prompt_comparative` not `strict_eq`" rationale: [ARCHITECTURE.md](ARCHITECTURE.md).

---

## Aggregation Logic

`_aggregate` only considers **eligible** records: `fetch_status == "ok"`, not a duplicate domain, not low-credibility, not stale/undated (v2.8), and authorized under the claim's declared source-authority policy if one was set (v2.8). Let `support`/`oppose` be the count of eligible `Supported`/`NotSupported` verdicts, and `independent_total` be the total eligible count.

| Final verdict | Exact condition |
|---|---|
| **InsufficientEvidence** | `independent_total < 2` — not enough independent, credible, fresh, authorized, reachable sources to say anything |
| **Verified** | `support >= 2` **and** `support > oppose` |
| **Refuted** | `oppose >= 2` **and** `oppose > support` |
| **Disputed** | Neither above, but `support > 0` **and** `oppose > 0` (a tie or near-tie) |
| **Unverified** | Everything else — enough sources exist but they're inconclusive |

**Tested nuance:** `Verified`/`Refuted` require a strict majority, not unanimity — a 2-vs-1 split is still `Verified`, not `Disputed` (`test_majority_with_dissent_still_verifies` in `tests/test_aggregation.py`). Full rationale in [DESIGN_DECISIONS.md § 6](DESIGN_DECISIONS.md#6-why-conservative-aggregation).

---

## Public Interface

```python
submit_claim(claim_text: str, source_urls: list[str], expected_domains: list[str] = []) -> str   # returns claim_id
get_claim(claim_id: str) -> str      # full JSON evidence record
get_verdict(claim_id: str) -> str    # just the final verdict word
total_claims() -> int
```

`expected_domains` (new in v2.8, optional): a bare domain (`"reuters.com"`) or full URL per entry; see [Source-Authority & Freshness Policy (v2.8)](#source-authority--freshness-policy-v28) above.

Example `get_claim` result:

```json
{
  "claim_id": "0",
  "claim_text": "The Eiffel Tower is located in Paris, France.",
  "final_verdict": "Verified",
  "total_sources_submitted": 3,
  "independent_domain_count": 3,
  "duplicate_domain_count": 0,
  "failed_source_count": 0,
  "stale_source_count": 0,
  "unauthorized_domain_count": 0,
  "expected_domains": [],
  "sources": [
    {
      "url": "https://reuters.example/eiffel-tower",
      "domain": "reuters.example",
      "is_duplicate_domain": false,
      "is_low_credibility": false,
      "is_authorized_domain": true,
      "fetch_status": "ok",
      "verdict": "Supported",
      "freshness": "Current",
      "is_stale": false
    }
  ]
}
```

*As of this revision, `domain` is the approximate **registrable** domain (see [DESIGN_DECISIONS.md § 8](DESIGN_DECISIONS.md#8-why-an-approximate-registrable-domain-not-a-full-public-suffix-list)), not necessarily the exact fetched hostname — the exact URL is always available in the `url` field. `stale_source_count`, `unauthorized_domain_count`, `expected_domains`, `is_authorized_domain`, `freshness`, and `is_stale` are new in v2.8 (see above); every other field is unchanged from the prior schema.*

---

## Security & Threat Model (Summary)

Prompt injection (both via fetched content and via the claim text itself), fake-news domains, Sybil-style duplicate-domain stuffing, fetch failures, and weak/speculative evidence are all explicitly mitigated with tests. Full threat model, evidence, and residual risks: **[SECURITY.md](SECURITY.md)**.

---

## Known Limitations (Summary)

No full Public Suffix List, no cross-domain content-similarity detection, a static (not governance-managed) denylist, no spam/staking defense, and consensus reliability that inherently scales with source count. Every limitation is disclosed with its specific trade-off reasoning, not hidden: **[SECURITY.md § 8](SECURITY.md#8-known-limitations-not-fixed-by-design)** and **[DESIGN_DECISIONS.md](DESIGN_DECISIONS.md)**. What a future version could do about each: **[ROADMAP.md](ROADMAP.md)**.

---

## Testing (Summary)

**111/111 offline tests passing**, organized into 8 files by function under test:

```bash
python3 -m unittest discover -s tests -p "test_*.py" -v
```

| File | Tests | Covers |
|---|---|---|
| `test_domain_extraction.py` | 26 | Registrable-domain extraction, subdomains, IPv6, trailing dots, `expected_domains` normalization (v2.8) |
| `test_content_classification.py` | 11 | Malformed/empty/ok content detection |
| `test_aggregation.py` | 15 | Final-verdict decision rule, incl. staleness + authorization gating (v2.8) |
| `test_parser.py` | 8 | Raw LLM response → fixed vocabulary |
| `test_prompt_and_consensus.py` | 12 | Prompt guardrails (incl. freshness, v2.8), equivalence principle |
| `test_input_validation.py` | 9 | Pre-fetch validation, `gl.vm.UserError` |
| `test_end_to_end.py` | 22 | Full pipeline, adversarial scenarios, `expected_domains` + freshness (v2.8) |
| `test_storage.py` | 8 | On-chain persistence, multi-claim isolation |

Plus an unexecuted `gltest` integration example (`tests/gltest_integration_example.py` — explicitly marked as not-yet-validated) and real live deployment evidence (not yet covering v2.8 — see the warning above). Full three-tier explanation: **[TESTING.md](TESTING.md)**.

---

## Deploying

Single-file deployment, same as any GenLayer Intelligent Contract — deploy `contract.py` via the GenLayer Studio "Create New Contract" UI (paste or upload the file; the constructor takes no arguments).

This exact contract is already deployed and live — see [Live Deployment](#live-deployment) above, including the v2.8 source-authority/freshness policy, which has its own dedicated live transactions at the current address.

---

## Repository Structure

```
truthbeacon/
├── contract.py                   # the Intelligent Contract (single deployable file)
├── README.md                     # this file
├── ARCHITECTURE.md
├── SECURITY.md
├── DESIGN_DECISIONS.md
├── TESTING.md
├── CONTRIBUTING.md
├── CHANGELOG.md
├── ROADMAP.md
├── REVIEWER_GUIDE.md
├── PROJECT_OVERVIEW.md
├── SUBMISSION_CHECKLIST.md
├── RELEASE_NOTES_v2.md
└── tests/
    ├── README.md                 # test coverage index
    ├── _bootstrap.py             # shared offline-stub wiring
    ├── genlayer_stub/            # minimal offline genlayer SDK stub
    ├── test_domain_extraction.py
    ├── test_content_classification.py
    ├── test_aggregation.py
    ├── test_parser.py
    ├── test_prompt_and_consensus.py
    ├── test_input_validation.py
    ├── test_end_to_end.py
    ├── test_storage.py
    └── gltest_integration_example.py   # unexecuted, see TESTING.md
```
