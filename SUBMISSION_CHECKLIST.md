# Submission Checklist

Use this before submitting TruthBeacon to GenLayer review. Each item states what's actually been verified, not just what should exist.

---

## Repository

- [x] `contract.py` is a single, self-contained deployable file (GenLayer contracts must be single-file)
- [x] `contract.py` compiles cleanly (`python3 -m py_compile contract.py`)
- [x] No `TODO`/`FIXME`/placeholder code anywhere in `contract.py`
- [x] Every GenLayer API call verified against current official SDK documentation ([CHANGELOG.md § SDK Compatibility Audit](CHANGELOG.md#v24--sdk-compatibility-audit))
- [x] README, ARCHITECTURE.md, SECURITY.md, DESIGN_DECISIONS.md, TESTING.md, CHANGELOG.md, ROADMAP.md, CONTRIBUTING.md all present and cross-linked
- [x] No dead code, no duplicated explanations across documents (verified during the documentation review pass)
- [ ] **Action needed:** push the final repository state to a public GitHub repository (this has not been done from within this environment — see [REVIEWER_GUIDE.md](REVIEWER_GUIDE.md) for what to upload)

## Tests

- [x] Offline test suite passes: **87/87**, run via `python3 -m unittest discover -s tests -p "test_*.py" -v`
- [x] Test coverage checklist complete — every requested scenario (valid claims, insufficient sources, duplicate domains, malformed URLs, timeouts, empty/malformed content, low-credibility domains, aggregation, parsing, registrable-domain extraction, boundary values, storage persistence) mapped to a specific test file in [tests/README.md](tests/README.md)
- [x] `gltest_integration_example.py` clearly and honestly marked as unexecuted, with the exact reason (no live node/`pytest` available in this environment)
- [x] Tests organized by function-under-test across 8 files, not one monolithic file

## Deployment

- [x] Contract successfully deployed to GenLayer Studio
- [x] Current contract address recorded: `0xE30A0F67Da4a3F58F2E31C82dfbc50e8B8F588A5` (redeployed after fixing GenVM lint rule E022 — see [CHANGELOG.md § v2.7](CHANGELOG.md#v27--genvm-lint-fix-e022-and-redeployment-current))
- [x] Redeployed source passes GenVM lint (no E022 diagnostics)
- [x] At least one successful `submit_claim` transaction with a clean `Verified` result on the current address (Eiffel Tower claim, 2/2 independent sources supporting, 1 correctly recorded as inaccessible)
- [x] Consensus finalized on the current address with no execution errors
- [x] Prior address (`0xF7275bA620A2a405905f8d93356012166753a62A`, historical) — deploy transaction reached FINALIZED/SUCCESS with 5/5 validator agreement
- [x] Prior address — at least one transaction demonstrating conservative behavior (`Unverified`/`InsufficientEvidence`) when evidence was incomplete
- [x] Prior address — at least one transaction demonstrating live duplicate-domain detection
- [x] Prior address — at least one transaction demonstrating input-validation rejection with consensus on the rejection itself

## Explorer

- [x] Public contract address page confirmed live and accessible (current): https://explorer-studio.genlayer.com/address/0xE30A0F67Da4a3F58F2E31C82dfbc50e8B8F588A5
- [x] Public contract address page confirmed live and accessible (prior, historical): https://explorer-studio.genlayer.com/address/0xF7275bA620A2a405905f8d93356012166753a62A
- [x] Individual transaction links recorded for each demonstration scenario (see [REVIEWER_GUIDE.md](REVIEWER_GUIDE.md))

## GitHub

- [ ] **Action needed:** create a public GitHub repository
- [ ] **Action needed:** push `contract.py`, all `.md` documentation files, and the `tests/` directory
- [ ] **Action needed:** copy the repository URL into the GenLayer Portal submission form's Evidence URL field

## Contribution (GenLayer Portal Submission)

- [ ] Contribution Type: **Builder** → **Projects**
- [ ] Title filled in (suggested: "TruthBeacon v2 — Corroborated AI Fact-Checking Contract")
- [ ] Notes/Description filled in (see [REVIEWER_GUIDE.md](REVIEWER_GUIDE.md) or the deployment evidence document for ready-to-use text)
- [ ] Evidence URLs added:
  - [ ] GitHub repository link
  - [ ] Live contract address page (primary evidence — proves everything else)
  - [ ] Deploy transaction link
  - [ ] At least the "clean Verified" and "duplicate-domain detection" transaction links

## Evidence

- [x] Every claim made in any `.md` file is backed by either a specific test name, a specific transaction hash, or an explicit "not yet verified" disclosure — no unbacked claims
- [x] Conservative/negative results (`Unverified`, `InsufficientEvidence`, rejections) are included alongside the positive `Verified` result, not cherry-picked away — this is itself evidence of honest behavior
- [x] `gltest_integration_example.py` explicitly disclosed as unexecuted rather than presented as a passing test

## Documentation

- [x] README rewritten to remove duplication and act as a navigation hub (see [CHANGELOG.md § v2.6](CHANGELOG.md#v26--full-documentation-suite-current))
- [x] ARCHITECTURE.md — diagrams, execution flow, storage/consensus model
- [x] SECURITY.md — full threat model with per-attack evidence
- [x] DESIGN_DECISIONS.md — every choice with alternatives and trade-offs
- [x] TESTING.md — three-tier testing explanation
- [x] CONTRIBUTING.md — contributor guide
- [x] CHANGELOG.md — full version history
- [x] ROADMAP.md — future work with rationale for current scope
- [x] REVIEWER_GUIDE.md — verification guide for judges
- [x] PROJECT_OVERVIEW.md — 5-minute executive summary
- [x] This file (SUBMISSION_CHECKLIST.md)
- [x] RELEASE_NOTES_v2.md

---

## Final Status

**Code and testing: ready.** **Documentation: ready.** **Live deployment: ready.**
**Remaining action items before submission are entirely administrative** (create/push to a public GitHub repo, then fill in the Portal form) — no further code, test, or documentation work is required.
