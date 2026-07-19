# Specification Process Baseline

## Authorities

| File | Status | Approved SHA-256 |
|---|---|---|
| `SPEC.md` | FROZEN | `01a30b5fcfd728bb8c334fdb76173e4d83e2667fc9b97a05672ce773f80e238e` |
| `PLAN.md` | FROZEN | `571c5b4cbbede66039cb6531b5512ea41a8c187d4a86225331e8d66b2ad6d37f` |

`SPEC.md` defines MVP behavior and acceptance semantics. `PLAN.md` defines work-package ownership, Planned Verification records, files, and test scheduling. This document records process evidence only and does not redefine either authority.

## Requirement and PV ledger schema

Each record preserves: Requirement ID, original requirement reference, Planned Verification ID, owning phase, owning package, owning day, supporting packages, planned category raw value, normalized planned categories, exact planned node/case, status, final evidence category raw value, normalized final categories, and evidence references.

Ownership is the single phase/package/day tuple in the PLAN traceability row. Supporting packages are verification contributors, never additional owners. Status begins at `PLANNED`; only the owner may first set `IN_PROGRESS` or `IMPLEMENTED`, and `VERIFIED` requires all supporting verification.

The PLAN planned category and SPEC Appendix H final evidence category are separate fields. Neither replaces the other.

## Change, scope, and retirement ledgers

A design-change record contains: Change/Requirement ID, date/time, rationale (reason proposed), original semantics and frozen text reference, proposed semantics, scope impact, 45-day plan impact, migration impact, test impact, major contribution impact, risk impact, approval status, and approval evidence/approver. No design change has been proposed at WP-01: `NONE`.

A scope-expansion impact record contains: expansion ID, proposed capability, MVP/stretch classification, affected Requirements/PVs, ownership/day/file/test impact, security and acceptance impact, approval state, and evidence reference.

A retired-ID record contains: retired Requirement/PV ID, date/time, reason, replacement ID or `NONE`, approval reference, and preserved historical evidence links. There are no retired IDs at WP-01.

## Evidence ledger

Each entry contains: evidence ID, Requirement/PV ID, category layer (`PLANNED` or `FINAL`), category raw value, exact artifact/node/command, observed result, producer role, date/time, status, and supporting-package completion references.

Future supporting evidence slots remain `PENDING`: CI evidence, cold-start verification, six-document closure, the second commit, and WP-01 completion. Passing a WP-01 planning test does not change any Requirement from `PLANNED`.

## WP-01 evidence state

- Frozen baseline commit: recorded.
- Linked worktree and controlled-file baseline: recorded.
- Pytest environment bootstrap: recorded in `AGENT_LOG.md`.
- Collection and expected Red: recorded in `AGENT_LOG.md` after execution.
- Specification remediation re-review: `APPROVED`; initial code quality review: `CHANGES_REQUIRED`; remediation is recorded in `AGENT_LOG.md`.
- Final code quality re-review: `APPROVED`; authority-table boundary, malformed-row, duplicate-owner mutation, and CQ-1..CQ-5 checks all passed with zero findings.
- Final verification by the main agent: `COMPLETED`.
- Stage, cold-start, final CI evidence, and second commit: `PENDING`.
- WP-01 completion: `PENDING`.
- The first code-quality re-review returned `CHANGES_REQUIRED` (Important 2, Minor 1); authority-table boundary remediation and isolated mutation evidence are recorded in `AGENT_LOG.md`. Post-remediation reviewer `/root/wp01_quality_final_rereviewer` returned `APPROVED` with all checks passing.
