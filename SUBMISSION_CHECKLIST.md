# Submission Checklist

Use this before submitting TruthBeacon to GenLayer review. Each item states what's actually been verified, not just what should exist.

---

## Repository

- [x] `contract.py` is a single, self-contained deployable file (GenLayer contracts must be single-file)
- [x] `contract.py` compiles cleanly (`python3 -m py_compile contract.py`)
- [x] No `TODO`/`FIXME`/placeholder code anywhere in `contract.py`
- [x] Every GenLayer API call verified against current official SDK documentation ([CHANGELOG.md § SDK Compatibility Audit](CHANGELOG.md#v24--sdk-compatibility-audit))
- [x] README, ARCHITECTURE.md, SECURITY.md, DESIGN_DECISIONS.md, TESTING.md, CHANGELOG.md, ROADMAP.md, CONTRIBUTING.md all present, cross-linked, and updated for v2.8
- [x] No dead code, no duplicated explanations across documents (verified during the documentation review pass)
- [x] Pushed to a public GitHub repository: https://github.com/123Cryp/genlayer-truthbeacon

## Tests

- [x] Offline test suite passes: **111/111**, run via `python3 -m unittest discover -s tests -p "test_*.py" -v`
- [x] Test coverage checklist complete — every requested scenario (valid claims, insufficient sources, duplicate domains, malformed URLs, timeouts, empty/malformed content, low-credibility domains, source-authority policy, freshness/staleness, aggregation, parsing, registrable-domain extraction, boundary values, storage persistence) mapped to a specific test file in [tests/README.md](tests/README.md)
- [x] `gltest_integration_example.py` clearly and honestly marked as unexecuted, with the exact reason (no live node/`pytest` available in this environment)
- [x] Tests organized by function-under-test across 8 files, not one monolithic file
- [x] v2.8 additions (`expected_domains`, freshness gating) covered by 24 new tests with zero reduction in prior coverage — every pre-v2.8 scenario still passes

## Deployment

- [x] Contract successfully deployed to GenLayer Studio
- [x] **Current (v2.8) contract address recorded:** `0x93F0F657a008FC99a41149E444AA37a604A14580` (redeployed for the source-authority policy + freshness signal — see [CHANGELOG.md § v2.8](CHANGELOG.md#v28--source-authority-policy--freshness-signal-current))
- [x] `expected_domains` source-authority policy verified live: unauthorized source correctly fetched, judged, and excluded from corroboration (tx `0x1891eb4645f426774c0301e3e9c7069d6fc253747381ed7672d7ef710afb5296`, FINALIZED)
- [x] Freshness/staleness signal verified live: a 2018 archived snapshot correctly judged `Stale` and excluded from corroboration (tx `0x760cdaa2fefec430d5b2896643b546255d500c9028c9bad01d759e4826e98a54`, FINALIZED)
- [x] Consensus finalized on both v2.8 transactions with no execution errors
- [x] Prior (post-E022) address (`0xE30A0F67Da4a3F58F2E31C82dfbc50e8B8F588A5`, historical) — clean `Verified` verification transaction, FINALIZED, no execution errors
- [x] Original prior address (`0xF7275bA620A2a405905f8d93356012166753a62A`, historical) — deploy transaction reached FINALIZED/SUCCESS with 5/5 validator agreement
- [x] Original prior address — at least one transaction demonstrating conservative behavior (`Unverified`/`InsufficientEvidence`) when evidence was incomplete
- [x] Original prior address — at least one transaction demonstrating live duplicate-domain detection
- [x] Original prior address — at least one transaction demonstrating input-validation rejection with consensus on the rejection itself

## Explorer

- [x] Public contract address page confirmed live and accessible (current, v2.8): https://explorer-studio.genlayer.com/address/0x93F0F657a008FC99a41149E444AA37a604A14580
- [x] Public contract address page confirmed live and accessible (prior, post-E022, historical): https://explorer-studio.genlayer.com/address/0xE30A0F67Da4a3F58F2E31C82dfbc50e8B8F588A5
- [x] Public contract address page confirmed live and accessible (original prior, historical): https://explorer-studio.genlayer.com/address/0xF7275bA620A2a405905f8d93356012166753a62A
- [x] Individual transaction links recorded for each demonstration scenario (see [REVIEWER_GUIDE.md](REVIEWER_GUIDE.md))

## GitHub

- [x] Public GitHub repository created: https://github.com/123Cryp/genlayer-truthbeacon
- [x] `contract.py`, all `.md` documentation files, and the `tests/` directory pushed
- [ ] **Action needed:** copy the repository URL into the GenLayer Portal submission form's Evidence URL field

## Contribution (GenLayer Portal Submission)

- [ ] Contribution Type: **Builder** → **Projects**
- [ ] Title filled in (suggested: "TruthBeacon v2.8 — Corroborated AI Fact-Checking Contract with Source-Authority & Freshness Policy")
- [ ] Notes/Description filled in (see [REVIEWER_GUIDE.md](REVIEWER_GUIDE.md) or the deployment evidence document for ready-to-use text)
- [ ] Evidence URLs added:
  - [ ] GitHub repository link (https://github.com/123Cryp/genlayer-truthbeacon)
  - [ ] Live contract address page, current v2.8 (primary evidence — proves everything else): https://explorer-studio.genlayer.com/address/0x93F0F657a008FC99a41149E444AA37a604A14580
  - [ ] Deploy transaction link
  - [ ] At least the `expected_domains` and freshness-gating transaction links (§4a in REVIEWER_GUIDE.md)

## Evidence

- [x] Every claim made in any `.md` file is backed by either a specific test name, a specific transaction hash, or an explicit "not yet verified" disclosure — no unbacked claims
- [x] Conservative/negative results (`Unverified`, `InsufficientEvidence`, rejections) are included alongside positive results, not cherry-picked away — this is itself evidence of honest behavior. Notably, both v2.8 live transactions resolve to `InsufficientEvidence`, showing the new exclusion mechanisms actually excluding sources rather than merely being present in the code.
- [x] `gltest_integration_example.py` explicitly disclosed as unexecuted rather than presented as a passing test

## Documentation

- [x] README rewritten to remove duplication and act as a navigation hub (see [CHANGELOG.md § v2.6](CHANGELOG.md#v26--full-documentation-suite))
- [x] ARCHITECTURE.md — diagrams, execution flow, storage/consensus model, updated for v2.8
- [x] SECURITY.md — full threat model with per-attack evidence, including two new v2.8 threat sections
- [x] DESIGN_DECISIONS.md — every choice with alternatives and trade-offs, including two new v2.8 decisions
- [x] TESTING.md — three-tier testing explanation, updated test counts and v2.8 coverage
- [x] CONTRIBUTING.md — contributor guide
- [x] CHANGELOG.md — full version history through v2.8
- [x] ROADMAP.md — future work with rationale for current scope
- [x] REVIEWER_GUIDE.md — verification guide for judges, including both v2.8 live transactions
- [x] PROJECT_OVERVIEW.md — 5-minute executive summary, updated for v2.8
- [x] This file (SUBMISSION_CHECKLIST.md)
- [x] RELEASE_NOTES_v2.md, updated with a v2.8 addendum

---

## Final Status

**Code and testing: ready (111/111 offline, both v2.8 mechanisms live-verified).** **Documentation: ready.** **Live deployment: ready.** **GitHub: ready.**
**Remaining action items before submission are entirely administrative** (fill in the Portal form with the repository URL and evidence links above) — no further code, test, or documentation work is required.
