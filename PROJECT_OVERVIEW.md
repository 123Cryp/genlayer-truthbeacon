# TruthBeacon v2 — Project Overview

*A 5-minute summary for judges. For depth, see [REVIEWER_GUIDE.md](REVIEWER_GUIDE.md).*

---

## What It Is

A GenLayer Intelligent Contract that fact-checks claims by requiring **multiple independent sources** to corroborate them, rather than trusting a single page. Anyone submits a claim plus 3–6 candidate URLs; GenLayer validators fetch and judge each source with an LLM, reach consensus, and the contract stores a full auditable evidence trail on-chain.

## Why It Exists

An earlier version of this contract was **rejected** for checking exactly one caller-selected page with no way to verify trustworthiness or corroboration. This is the redesign — every clause of that rejection is directly addressed, with tests and (now) live deployment evidence behind each fix.

## What Makes It Notable

- **Corroboration, not trust:** requires ≥2 independent, credible sources to agree before claiming `Verified` or `Refuted`. One confident source is never enough.
- **Sybil-resistant:** detects when submitted URLs are really the same publisher (subdomains, mirrors) via registrable-domain matching — verified working on a live transaction.
- **Source-authority policy (v2.8):** claim creators can optionally lock in, at submission time, which domains are authorized to count as corroboration for that specific claim (`expected_domains`) — verified live: an unauthorized source was fetched and judged but correctly excluded from the count.
- **Freshness-aware (v2.8):** each source is independently judged `Current`/`Stale`/`Undated`, and stale/undated sources are excluded from corroboration exactly like duplicates and denylisted domains — verified live: a 2018 archived snapshot was correctly flagged `Stale` and excluded.
- **Honest under uncertainty:** live-tested with an undisputed fact (Neil Armstrong on the Moon) and correctly returned `Unverified` because one source failed to fetch and another was ambiguous — it does not default to a confident-sounding answer.
- **Consensus-correct:** uses `gl.eq_principle.prompt_comparative`, the SDK-correct primitive for LLM-derived output — a `strict_eq` misuse (a documented anti-pattern) was found and fixed during self-review, not shipped.
- **SDK-verified:** every GenLayer API call checked against current official documentation; one incorrect path (`gl.UserError`) was found and corrected.

## Proof, Not Just Claims

| | |
|---|---|
| Offline tests | **111/111 passing**, `python3 -m unittest discover -s tests -p "test_*.py"` |
| Live deployment (current, v2.8) | **Yes** — `0x93F0F657a008FC99a41149E444AA37a604A14580` on GenLayer Studio (redeployed for the source-authority + freshness policy, see [CHANGELOG.md § v2.8](CHANGELOG.md#v28--source-authority-policy--freshness-signal-current)) |
| Live transactions (current address) | **2** — one exercising `expected_domains` (an unauthorized source correctly excluded from corroboration), one exercising freshness gating (a stale archived source correctly excluded) — both `FINALIZED` |
| Live transactions (prior address, historical) | **6**, spanning a clean success, a conservative rejection, live duplicate-domain detection, and unanimous 5-validator input rejection — see [REVIEWER_GUIDE.md § 4](REVIEWER_GUIDE.md#4-live-transaction-evidence) |
| Public verification | https://explorer-studio.genlayer.com/address/0x93F0F657a008FC99a41149E444AA37a604A14580 |

## The One-Sentence Pitch

*A fact-checking contract that only says "Verified" when it's actually earned it — and proves that, live, on-chain, with receipts.*

## Where to Go Next

- **Verify a claim in 2 minutes:** [REVIEWER_GUIDE.md § 4](REVIEWER_GUIDE.md#4-live-transaction-evidence) — the current live transaction plus six prior-deployment transaction hashes, what each proves
- **Understand the design:** [ARCHITECTURE.md](ARCHITECTURE.md)
- **See the threat model:** [SECURITY.md](SECURITY.md)
- **See what's honestly not solved:** [SECURITY.md § 8](SECURITY.md#8-known-limitations-not-fixed-by-design), [ROADMAP.md](ROADMAP.md)
