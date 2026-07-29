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
- **Honest under uncertainty:** live-tested with an undisputed fact (Neil Armstrong on the Moon) and correctly returned `Unverified` because one source failed to fetch and another was ambiguous — it does not default to a confident-sounding answer.
- **Consensus-correct:** uses `gl.eq_principle.prompt_comparative`, the SDK-correct primitive for LLM-derived output — a `strict_eq` misuse (a documented anti-pattern) was found and fixed during self-review, not shipped.
- **SDK-verified:** every GenLayer API call checked against current official documentation; one incorrect path (`gl.UserError`) was found and corrected.

## Proof, Not Just Claims

| | |
|---|---|
| Offline tests | **87/87 passing**, `python3 -m unittest discover -s tests -p "test_*.py"` |
| Live deployment | **Yes** — `0xF7275bA620A2a405905f8d93356012166753a62A` on GenLayer Studio |
| Live transactions | **5**, spanning a clean success, a conservative rejection, live duplicate-domain detection, and unanimous 5-validator input rejection |
| Public verification | https://explorer-studio.genlayer.com/address/0xF7275bA620A2a405905f8d93356012166753a62A |

## The One-Sentence Pitch

*A fact-checking contract that only says "Verified" when it's actually earned it — and proves that, live, on-chain, with receipts.*

## Where to Go Next

- **Verify a claim in 2 minutes:** [REVIEWER_GUIDE.md § 4](REVIEWER_GUIDE.md#4-live-transaction-evidence) — six real transaction hashes, what each proves
- **Understand the design:** [ARCHITECTURE.md](ARCHITECTURE.md)
- **See the threat model:** [SECURITY.md](SECURITY.md)
- **See what's honestly not solved:** [SECURITY.md § 8](SECURITY.md#8-known-limitations-not-fixed-by-design), [ROADMAP.md](ROADMAP.md)
