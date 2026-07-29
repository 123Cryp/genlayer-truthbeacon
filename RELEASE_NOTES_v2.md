# Release Notes — TruthBeacon v2

## Overview

TruthBeacon v2 is a complete redesign of a previously rejected GenLayer Intelligent Contract, addressing every clause of the original reviewer feedback, followed by two independent critical self-review rounds, a dedicated SDK compatibility audit, and a live deployment to GenLayer Studio.

---

## Headline Achievements

- **Multi-source corroboration** replaces single-page verification: 3–6 required sources, ≥2 independent agreeing sources required for any confident verdict.
- **Duplicate/Sybil-domain detection** via approximate registrable-domain matching — verified live on Studio (Eiffel Tower transaction, two `wikipedia.org` URLs correctly deduplicated).
- **Full on-chain provenance**: every source's URL, domain, duplicate/denylist status, fetch outcome, and verdict is persisted and auditable via `get_claim`.
- **Correct consensus primitive**: uses `gl.eq_principle.prompt_comparative`, not `strict_eq` — a documented anti-pattern for LLM-derived output that was present in an earlier draft and actively found and fixed.
- **SDK-verified**: every GenLayer API call (`gl.vm.UserError`, `gl.public.write`/`view`, `TreeMap`, `u256`, `gl.nondet.web.render`, `gl.nondet.exec_prompt`, `gl.eq_principle.prompt_comparative`) checked against current official documentation. One incorrect API path (`gl.UserError` → `gl.vm.UserError`) was found and fixed.
- **87 passing offline tests** across 8 organized files, plus a documented (unexecuted) live-integration example.
- **Live deployment**: 5 real transactions on GenLayer Studio, covering a clean `Verified` result, a conservative `Unverified` result, live duplicate-domain detection, and unanimous 5-validator rejection of invalid input.

---

## What Changed From the Rejected v1

| Aspect | v1 (rejected) | v2 (this release) |
|---|---|---|
| Sources per claim | Exactly 1 | 3–6 required |
| Corroboration | None | ≥2 independent agreeing sources required |
| Duplicate detection | None | Registrable-domain-based, subdomain-aware |
| Low-credibility handling | None | Static denylist, excluded from corroboration |
| Fetch failure handling | Undifferentiated | Explicit `timeout`/`inaccessible`/`empty`/`malformed` classification |
| On-chain evidence | Verdict only | Full per-source provenance trail |
| Prompt injection defense | None | Guards both source content and claim text |
| Consensus primitive | N/A (single fetch) | `gl.eq_principle.prompt_comparative` |
| Test coverage | Unknown/minimal | 87 offline tests, live deployment evidence |

---

## Review Rounds Summary

Three dedicated adversarial self-review passes were conducted (full detail in [CHANGELOG.md](CHANGELOG.md)):

1. **Round 1** — found and fixed the `strict_eq` misuse (Critical), a claim-text prompt-injection gap (Critical), 7 other issues.
2. **Round 2 (fresh-eyes)** — found and fixed a verdict-matching whitespace bug, a missing end-to-end test for the `Refuted` verdict, 3 other issues.
3. **SDK Compatibility Audit** — found and fixed the `gl.UserError` → `gl.vm.UserError` API path error, confirmed every other API call correct.

Test count grew from 58 → 87 over these rounds. No functionality was ever removed; every fix added coverage or corrected an actual defect.

---

## Live Deployment Summary

**Contract address:** `0xF7275bA620A2a405905f8d93356012166753a62A`
**Explorer:** https://explorer-studio.genlayer.com/address/0xF7275bA620A2a405905f8d93356012166753a62A

| Transaction | Result | Proves |
|---|---|---|
| Deploy | SUCCESS, 5/5 Agree | Contract deploys cleanly on real GenVM |
| Apollo 11 claim | `Verified` | Clean multi-source agreement works end-to-end |
| Neil Armstrong claim | `Unverified` | Conservative aggregation holds even for undisputed facts, live |
| Eiffel Tower claim | `InsufficientEvidence` | Duplicate-domain detection works live, not just in mocked tests |
| Invalid 2-source claim | Rejected, 5/5 identical error | Deterministic pre-flight validation works before any fetch/LLM cost |

Full detail: [REVIEWER_GUIDE.md](REVIEWER_GUIDE.md).

---

## What This Release Does NOT Include

Deliberately out of scope, each with a specific reason documented in [ROADMAP.md](ROADMAP.md):
- Full Public Suffix List support
- Governance-managed reputation registry
- Cryptographic/signed source provenance
- Spam resistance / staking
- Cross-domain content-similarity detection
- Evidence weighting / reputation scoring

---

## Upgrade Notes

This is the current and only deployed version. There is no v1 deployment to migrate from — v1 was rejected before deployment.
