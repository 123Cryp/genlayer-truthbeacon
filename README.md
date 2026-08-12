# TruthBeacon v2 — Corroborated AI Fact-Checking on GenLayer

TruthBeacon is a GenLayer Intelligent Contract for decentralized fact-checking. Anyone submits a claim together with candidate source URLs; GenLayer's validators independently fetch and judge each source, and reach Optimistic Democracy consensus on one deterministic final verdict, stored permanently on-chain with a full, auditable evidence trail.

This is a from-scratch redesign of a previously **rejected** version of this contract (see [Reviewer Feedback Addressed](#reviewer-feedback-addressed) below), and has since been **deployed and tested live on GenLayer Studio** (see [Live Deployment](#live-deployment)).

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

**Contract address:** `0xE30A0F67Da4a3F58F2E31C82dfbc50e8B8F588A5`
**Public explorer (all transactions):** https://explorer-studio.genlayer.com/address/0xE30A0F67Da4a3F58F2E31C82dfbc50e8B8F588A5

This is not just a tested contract — it is a **deployed and exercised** one. This is a redeployment following a lint fix (GenVM rule E022 — internal helper methods refactored from `@classmethod`/`@staticmethod` to plain instance methods with `self`; no business logic changed, see [CHANGELOG.md](CHANGELOG.md)). On this current address, a live `submit_claim` transaction reached a `Verified` verdict from 2 independent corroborating sources, with a third, inaccessible source correctly recorded as failed rather than silently dropped, and consensus finalized across validators with no execution errors. The prior deployment (superseded by this redeployment) was exercised with six transactions covering clean success, conservative rejection under incomplete evidence, live duplicate-domain detection, and unanimous multi-validator input rejection — full detail, clearly labeled as prior-deployment evidence, is in [REVIEWER_GUIDE.md](REVIEWER_GUIDE.md) and [TESTING.md § Tier 3](TESTING.md#4-tier-3--live-deployment-evidence).

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

## Architecture (Summary)

```
submit_claim(claim_text, source_urls)
        │
        ├─ 1. Deterministic input validation (cheap, fails fast, no gl.* calls)
        │      claim_text ≤ MAX_CLAIM_TEXT_CHARS · 3 ≤ len(source_urls) ≤ 6
        │      ≥ 2 distinct, non-denylisted domains among submitted URLs
        │
        ├─ 2. Deterministic provenance annotation (_annotate_sources)
        │      registrable domain per URL · duplicate flag · denylist flag
        │
        ├─ 3. ONE non-deterministic closure (gl.eq_principle.prompt_comparative)
        │      per source: fetch → classify → LLM judge → fixed-vocabulary verdict
        │      then deterministic aggregation → one final verdict + stats
        │
        └─ 4. Persist claim + verdict + full evidence trail to on-chain storage
```

Full component diagrams, sequence diagrams, and the "why `prompt_comparative` not `strict_eq`" rationale: [ARCHITECTURE.md](ARCHITECTURE.md).

---

## Aggregation Logic

`_aggregate` only considers **eligible** records: `fetch_status == "ok"`, not a duplicate domain, not low-credibility. Let `support`/`oppose` be the count of eligible `Supported`/`NotSupported` verdicts, and `independent_total` be the total eligible count.

| Final verdict | Exact condition |
|---|---|
| **InsufficientEvidence** | `independent_total < 2` — not enough independent, credible, reachable sources to say anything |
| **Verified** | `support >= 2` **and** `support > oppose` |
| **Refuted** | `oppose >= 2` **and** `oppose > support` |
| **Disputed** | Neither above, but `support > 0` **and** `oppose > 0` (a tie or near-tie) |
| **Unverified** | Everything else — enough sources exist but they're inconclusive |

**Tested nuance:** `Verified`/`Refuted` require a strict majority, not unanimity — a 2-vs-1 split is still `Verified`, not `Disputed` (`test_majority_with_dissent_still_verifies` in `tests/test_aggregation.py`). Full rationale in [DESIGN_DECISIONS.md § 6](DESIGN_DECISIONS.md#6-why-conservative-aggregation).

---

## Public Interface

```python
submit_claim(claim_text: str, source_urls: list[str]) -> str   # returns claim_id
get_claim(claim_id: str) -> str      # full JSON evidence record
get_verdict(claim_id: str) -> str    # just the final verdict word
total_claims() -> int
```

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
  "sources": [
    {
      "url": "https://reuters.example/eiffel-tower",
      "domain": "reuters.example",
      "is_duplicate_domain": false,
      "is_low_credibility": false,
      "fetch_status": "ok",
      "verdict": "Supported"
    }
  ]
}
```

*As of this revision, `domain` is the approximate **registrable** domain (see [DESIGN_DECISIONS.md § 8](DESIGN_DECISIONS.md#8-why-an-approximate-registrable-domain-not-a-full-public-suffix-list)), not necessarily the exact fetched hostname — the exact URL is always available in the `url` field.*

---

## Security & Threat Model (Summary)

Prompt injection (both via fetched content and via the claim text itself), fake-news domains, Sybil-style duplicate-domain stuffing, fetch failures, and weak/speculative evidence are all explicitly mitigated with tests. Full threat model, evidence, and residual risks: **[SECURITY.md](SECURITY.md)**.

---

## Known Limitations (Summary)

No full Public Suffix List, no cross-domain content-similarity detection, a static (not governance-managed) denylist, no spam/staking defense, and consensus reliability that inherently scales with source count. Every limitation is disclosed with its specific trade-off reasoning, not hidden: **[SECURITY.md § 8](SECURITY.md#8-known-limitations-not-fixed-by-design)** and **[DESIGN_DECISIONS.md](DESIGN_DECISIONS.md)**. What a future version could do about each: **[ROADMAP.md](ROADMAP.md)**.

---

## Testing (Summary)

**87/87 offline tests passing**, organized into 8 files by function under test:

```bash
python3 -m unittest discover -s tests -p "test_*.py" -v
```

| File | Tests | Covers |
|---|---|---|
| `test_domain_extraction.py` | 18 | Registrable-domain extraction, subdomains, IPv6, trailing dots |
| `test_content_classification.py` | 11 | Malformed/empty/ok content detection |
| `test_aggregation.py` | 9 | Final-verdict decision rule |
| `test_parser.py` | 8 | Raw LLM response → fixed vocabulary |
| `test_prompt_and_consensus.py` | 11 | Prompt guardrails, equivalence principle |
| `test_input_validation.py` | 9 | Pre-fetch validation, `gl.vm.UserError` |
| `test_end_to_end.py` | 13 | Full pipeline, adversarial scenarios |
| `test_storage.py` | 8 | On-chain persistence, multi-claim isolation |

Plus an unexecuted `gltest` integration example (`tests/gltest_integration_example.py` — explicitly marked as not-yet-validated) and real live deployment evidence. Full three-tier explanation: **[TESTING.md](TESTING.md)**.

---

## Deploying

Single-file deployment, same as any GenLayer Intelligent Contract — deploy `contract.py` via the GenLayer Studio "Create New Contract" UI (paste or upload the file; the constructor takes no arguments).

This exact contract is already deployed and live — see [Live Deployment](#live-deployment) above.

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
