# Task: Implement hybrid agent-guided bootstrap

## Objective

Add an optional provider-neutral skill and stable machine-readable protocol that let an LLM inspect and adapt recommendations to a destination project while the deterministic core remains authoritative for rendering, ownership, plan integrity, apply, rollback, and validation.

## Architecture impact

- **ADR required:** Yes
- **Accepted decision:** ADR-0005
- **Relevant accepted ADRs:** ADR-0001, ADR-0002, ADR-0003
- **Implementation gate:** Do not begin architecture-dependent implementation until ADR-0005 is independently reviewed, revised, and explicitly accepted by a human.

## Phases and acceptance criteria

### Phase 0: Decide

- [x] Draft ADR-0005 as Proposed.
- [x] Add ADR-0005 to the ADR index.
- [x] Complete independent architecture and security review.
- [x] Resolve initial review findings in the Proposed ADR.
- [x] Complete final independent review of the revised ADR.
- [x] Obtain explicit human acceptance before changing ADR-0005 to Accepted.

### Phase 1: Threat model, protocol, and safe facade

- [x] Document the trusted-caller, untrusted-agent, repository-content, manifest-provenance, and equal-permission filesystem boundaries.
- [x] Add strict schema-versioned inspection, intent, plan, and result models.
- [x] Add a field authority matrix in which agent artifacts contain proposals but cannot mark human-only values confirmed or authorized.
- [x] Add canonical JSON serialization and domain-separated stable plan identifiers.
- [x] Reject unknown fields, content/patch blobs, arbitrary paths, modes, mutability, credentials, and implicit privileged features.
- [x] Add a public facade that cannot accept arbitrary desired-file maps.
- [x] Route the CLI and facade through the same deterministic pipeline.

### Phase 2: Bounded inspection

- [x] Add root-confined, no-follow inspection of bounded regular files.
- [x] Exclude secrets, credentials, VCS, vendor/generated trees, binary files, and special files.
- [x] Enforce file-count, byte, directory-entry, and depth limits with truncation markers.
- [x] Return derived facts, paths, confidence, file types, and hashes by default.
- [x] Require separate consent before raw snippets are emitted for remote LLM use.
- [x] Never execute detected commands or enable network access during inspection.

### Phase 3: Agent-guided CLI workflow

- [x] Add read-only `inspect` with machine-readable output.
- [x] Add agent-guided dry-run and expected-plan flags to `init` and `retrofit`.
- [x] Include exact review data, sensitive selections, warnings, diffs, manifest-claim labels, and plan identifier.
- [x] Bind explicit target-root existence/type/symlink markers, normalized output paths, content hashes, modes, mutability, resulting ownership metadata, destination preconditions, and missing-state markers into the plan identifier.
- [x] Recompute rendered output and all destination preconditions before apply.
- [x] Require the skill to stop after proposal/preview and hand off to a separate interactive human invocation.
- [x] Require the trusted terminal to display the complete recomputed plan and obtain direct confirmation; an expected identifier must not suppress either step.
- [x] Reject `--yes` in agent-guided apply mode.
- [x] State and test that plan identifiers provide integrity, not approver identity or bearer authorization.
- [x] Preserve direct non-LLM workflows, legacy exit codes, idempotency, and explicit opt-ins.
- [x] Keep inspection and dry-run stdout-only with no filesystem or Git writes.

### Phase 4: Skills and platform delivery

- [x] Add canonical provider-neutral bootstrap/maintenance skill content to the package and generated project output where applicable.
- [x] Keep skill instructions free of provider-specific tool syntax.
- [x] Prohibit agent-callable apply unless a future verified host provides trustworthy user-presence authorization.
- [x] Do not automatically install or own user-scoped skill files.
- [x] Document manual packaged-skill loading and CLI/out-of-band advisor fallbacks.
- [x] Verify discovery and invocation contracts before updating platform support claims.
- [x] Keep hooks limited to explicit deterministic validation or drift reporting.

### Phase 5: Documentation, examples, and evidence

- [x] Update architecture and workflow documentation with trust, authority, plan-integrity, and human-handoff boundaries.
- [x] Update `docs/superpowers-spec.md` for the additive read-only `inspect` command after ADR acceptance.
- [x] Document the CLI protocol, public facade, conflicts, claimed manifest state, limitations, and non-goals.
- [x] Update generated-output documentation, golden fixtures, and checked-in examples.
- [x] Update platform support only with verified evidence.
- [x] Run the docs-check skill and record whether further ADR or documentation changes are required.

### Phase 6: Validation and review

- [x] Test inspection confinement, no-follow handling, exclusions, limits, truncation, and raw-snippet consent.
- [x] Test field authority and Markdown, Unicode, delimiter, newline, command, path, content, patch, and credential injection rejection.
- [x] Test canonical replay and plan-identifier sensitivity, including missing versus existing roots and changes to normalized output paths, mutability, executable modes, and resulting ownership entries.
- [x] Test changed requests, outputs, target aliases, manifest claims, file types, modes, symlinks, and stale state.
- [x] Test explicit opt-ins, unverified agent proposals, trusted-terminal display and confirmation, agent handoff, `--yes` rejection in agent-guided mode, and direct trusted-caller behavior.
- [x] Test unmanaged conflicts, mutable customization, obsolete removal, rollback, and idempotency.
- [x] Test legacy CLI compatibility and complete non-LLM operation.
- [x] Test generated skills and platform discovery contracts.
- [x] Run the full repository test suite and repository validator.
- [x] Run all-platform dry-run and generated-project validation.
- [x] Complete independent final review and record residual risks.

## Deferred decisions and explicit non-goals

- Replacing the deterministic CLI/core with an autonomous agent.
- Accepting arbitrary LLM-generated managed files, templates, paths, executables, manifests, credentials, or patches.
- Preserving as an explicit plan exception, overwriting, adopting, relinquishing, or semantically merging unmanaged files.
- Authenticating approver identity, bearer approvals, expiry, single-use approval, or multi-party authorization.
- Automatically installing user-scoped skills.
- Treating an LLM statement, a public plan identifier, or legacy `--yes` as agent-guided human authorization.
- Automatically enabling MCP, agents, workflows, schedules, hooks, permissions, network access, or removals.
- Executing detected project commands during inspection.
- Persisting audit artifacts during inspection or dry-run.
- Defending against a malicious local actor with equivalent filesystem permissions.
- Building a general migration or semantic-merge engine in the initial implementation.
- Changing versions, creating a release commit, or adding tags without a separate release request.

## Validation evidence

- Initial independent architecture and security review found unresolved authorization provenance, unmanaged-preservation contract drift, dry-run writes, inspection containment, skill distribution, command-surface, manifest-provenance, replay, and semantic-injection risks.
- ADR-0005 was revised to use human handoff, retain conflict-by-default behavior, keep dry-run stdout-only, define bounded inspection and field authority, narrow skill distribution claims, add `inspect` explicitly, and document manifest and filesystem threat boundaries.
- Final independent review found no remaining blocker and confirmed the trusted-terminal confirmation and plan-identifier binding requirements are decision-ready.
- Human accepted ADR-0005 on 2026-07-31 and authorized implementation of all phases.
- Full suite: `PYTHONPATH=src python3 -m unittest discover -s tests -v` — 97 tests passed, including installed Claude 2.1.170, Codex 0.145.0, and OpenCode 1.2.27 diagnostics plus Pi static/native-path contracts.
- Validators: `PYTHONPATH=src python3 -m agentic_bootstrap validate --target .` and `.agentic/bin/validate` passed.
- Documentation review: `.agentic/bin/docs-check` reported no heuristic gaps; manual review covered CLI/API, architecture, threat boundaries, support claims, generated output, examples, and ADR indexing.
- Dry-run and fixtures: canonical all-platform dry-run, agent-guided retrofit preview/no-write smoke, direct Pi init, generated validator, and target validation passed.
- Packaging: `python3 -m pip wheel . --no-deps` and isolated-wheel `inspect`, `init`, generated-skill presence, and `validate` smoke passed. `python3 -m build` was unavailable because the host `build` module has no executable entry point; the PEP 517 pip wheel succeeded instead.
- Installed platform versions observed: Claude Code 2.1.170, Codex CLI 0.145.0, OpenCode 1.2.27, and Pi 0.83.0. Pi has no separate automated CLI diagnostic in this repository; its native AGENTS/skills contract is statically tested.
- Independent implementation reviews found and resolved plan-review omissions, ancestor-symlink and special-file handling, Unicode/terminal-control rendering, raw existing-content disclosure, credential/generated exclusions, rollback-result gaps, and empty expected-plan handling. The conclusive review gate returned PASS with no blocker, high, or medium findings.
- Residual risks are the accepted ADR-0005 limits: public plan IDs do not authenticate humans, manifests are unauthenticated ownership claims, inspection cannot constrain extra host-granted reads, structural validation does not prove semantic safety, and equal-permission malicious filesystem races are out of scope.
