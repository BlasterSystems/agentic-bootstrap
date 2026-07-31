# ADR-0005: Agent-guided bootstrap with a deterministic core

- **Status:** Accepted
- **Date:** 2026-07-31
- **Decision owners:** Agentic Bootstrap maintainers
- **Scope:** Generator interface and trust boundary
- **Tags:** agents, llm, safety, portability, retrofit
- **Supersedes:** None
- **Superseded by:** None

## Context

Agentic Bootstrap currently exposes deterministic `init`, `retrofit`, and `validate` CLI workflows. Detection produces typed project facts, canonical templates and adapters render desired files, the planner classifies ownership-aware operations, and staged apply provides stale-plan checks, rollback, validation, and a manifest.

This model is safe and repeatable, but it has limited judgment when a destination contains partial agent configuration, unfamiliar project conventions, or ambiguous commands. A language model can inspect broader context, identify uncertainty, ask clarifying questions, and explain manual improvements. It cannot by itself provide the same guarantees for ownership, idempotency, structured serialization, authorization, rollback, or path safety.

The project needs a durable boundary between adaptive LLM guidance and trusted deterministic mutation. It must remain usable without an LLM and portable across supported coding platforms whose skill discovery, process invocation, and user-approval capabilities differ.

## Decision drivers

- Preserve deterministic safety, ownership, rollback, and idempotency guarantees.
- Improve retrofit evidence review and guidance for partially configured or unfamiliar projects.
- Keep the complete non-LLM CLI workflow available for humans and automation.
- Keep portable skill content free of provider-specific tool syntax.
- Prevent repository content or LLM output from silently enabling privileged integrations or introducing arbitrary managed files.
- Bind a reviewed plan to the exact request, rendered output, target state, and operations.
- Avoid claiming that a public digest authenticates a human or that structural validation establishes semantic trust.
- Support reproducible plans without storing secrets, requiring network access, or weakening dry-run.

## Considered options

### Keep deterministic CLI workflows only

The current architecture remains simple, fast, testable, and safe. Detection and templates can be expanded over time. This does not adequately address context-sensitive questioning, unfamiliar stacks, or explanation of existing conflicts.

### Add an out-of-band LLM advisor to the existing CLI

An LLM could inspect a project, ask questions, and produce a hardened answers file for the current CLI. This is a low-complexity way to improve typed facts while keeping apply unchanged. It does not produce a bounded inspection contract, bind a reviewed plan to its destination preconditions, or define a portable skill workflow. It remains a valid fallback when the agent-guided protocol or skill is unavailable.

### Trigger bootstrap mutation from a hook

A hook could run automatically when a repository is opened or changed. Implicit execution is unsuitable for informed authorization, hooks are not portable across supported platforms, and generation during unrelated lifecycle events would be surprising. Hooks remain suitable only for explicitly installed deterministic validation or drift reporting.

### Replace the CLI with an autonomous LLM agent

An agent can adapt output and semantically merge existing content, but arbitrary agent writes weaken determinism, structured serialization, ownership, replay, and rollback guarantees. This also makes CI and non-LLM use dependent on an agent runtime.

### Let an agent submit arbitrary desired files to the existing planner

The planner can constrain paths and preserve conflicting destinations, but its internal `GeneratedFile` input can contain arbitrary bytes, executable modes, mutable ownership metadata, workflows, hooks, or agent instructions. Filesystem safety does not establish content trust. Approving operation names alone would not bind review to exact generated content.

### Add an optional agent-guided layer over a deterministic protocol

A provider-neutral skill guides an LLM through bounded inspection, uncertainty resolution, typed intent, dry-run planning, human handoff, apply, and validation. The LLM remains advisory. A closed protocol and the deterministic renderer remain authoritative for managed paths, bytes, modes, ownership, and integrations. The existing CLI remains first-class and the protocol is available through machine-readable CLI output, with an optional Python facade.

## Decision

Adopt an optional agent-guided layer over the deterministic core with the following boundaries.

### Trust and authority model

1. **Inspection evidence is untrusted input.** Deterministic inspection is root-confined and no-follow. It examines bounded regular files only, skips symlinks and special files, excludes known secret, credential, vendor, generated, VCS, and binary locations, and enforces file-count and byte limits with truncation markers. Derived facts, source paths, confidence, file types, and hashes are returned by default. Raw snippets require separate explicit consent before they may be sent to a remote LLM. The protocol cannot restrict additional read access already granted to the surrounding agent runtime.
2. **Fields have explicit authority.** The LLM may recommend values but cannot confirm them on behalf of a human. Languages and components are evidence-derived. Project name and description are bounded human-confirmable prose. Build, test, and run commands and ticket conventions require direct confirmation in the trusted human invocation and are never executed during inspection. Platforms and every sensitive feature are human-only selections. Agent artifacts carry these values only as unverified proposals. Output paths, bytes, serializers, modes, mutability, manifest metadata, and operation policy are core-only.
3. **The LLM produces typed intent, not managed files.** Agent-facing input may contain only schema-defined proposed project facts, supported platform recommendations, and documented feature recommendations. It cannot mark any value human-confirmed or authorized. Unknown fields, arbitrary paths, content or patch blobs, credentials, executable modes, and manifest entries are rejected. Field validation covers length, control characters, Unicode normalization, Markdown delimiters, and command-context constraints; syntax validation is not represented as semantic safety.
4. **The deterministic renderer is authoritative.** Managed output originates only from canonical templates, serializers, and platform adapters through a validated typed request.

### Invocation and authorization model

5. **The CLI JSON protocol is the portable agent boundary.** Skills orchestrate a stable machine-readable command protocol instead of depending on Python imports. A public Python facade may support embedding, but it enforces the same schemas and cannot accept arbitrary desired-file maps.
6. **The existing CLI remains first-class.** Humans and automation can complete initialization, retrofit, dry-run planning, apply, and validation without an LLM. Agent-guided behavior is additive. The implementation adds a read-only `inspect` command and agent-guided flags to `init` and `retrofit`; it does not add separate `plan` or `apply` commands. The command-surface statement in `docs/superpowers-spec.md` must be updated when this ADR is accepted. Existing exit codes remain compatible.
7. **A plan identifier provides integrity, not identity.** Canonical SHA-256 with a domain-separated schema identifier covers the generator and protocol versions; normalized target path; explicit target-root existence, directory type, and symlink-state markers; normalized human-confirmed request; every normalized desired output path, content hash, executable mode, mutability value, and resulting manifest ownership entry; observed manifest state; destination existence and file-type markers, hashes, modes, and symlink state; operation classifications; and obsolete-removal policy. Missing values use explicit canonical markers. Timestamps are excluded. Apply recomputes all trusted output and preconditions and rejects mismatches.
8. **Initial agent-guided apply uses a trusted human handoff.** The skill must stop after producing an untrusted proposal and plan preview. A human separately invokes `init` or `retrofit` in an interactive terminal. That deterministic command recomputes the plan and identifier, displays the complete normalized facts, commands, platforms, sensitive selections, manifest-claim warnings, operations, and reviewable diffs through the trusted terminal, and requires direct confirmation before mutation. An agent-supplied identifier or proposal cannot suppress this display or confirmation; `--yes` is rejected in agent-guided apply mode. A supplied plan identifier is only an expected-integrity check against the recomputed plan, not a bearer capability or proof of who approved it. Agent-callable apply is prohibited unless a future verified host integration supplies trustworthy user-presence authorization. Existing direct CLI automation remains a separate trusted-caller mode and is not described as agent-guided authorization. The protocol cannot defend against a host that grants an untrusted agent unrestricted shell access; that is an external permission boundary.
9. **Plan identifiers are reusable integrity checks, not one-time approvals.** A changed request, confirmation, target-root state, normalized output path, content, ownership metadata, generator version, manifest, destination precondition, or operation changes the identifier and requires renewed review. Returning all bound state to an identical value can reproduce an identifier; the fresh trusted-terminal display and direct confirmation remain the authorization event. Authenticated, expiring, session-bound, or multi-party approvals are deferred.

### Ownership, conflicts, and filesystem model

10. **Existing conflict behavior remains unchanged initially.** Non-identical unmanaged destinations remain conflicts, conflicts abort apply, customized mutable seeds remain preserved under the existing manifest policy, and obsolete removal remains explicit. The LLM may explain manual resolution options but cannot overwrite, merge, adopt, relinquish, or exempt a conflicting path. `preserve unmanaged`, semantic patch export/application, and ownership adoption require a separate Proposed ADR because they would change the accepted safety contract and persistent ownership semantics.
11. **Manifest entries are ownership claims, not authenticated provenance.** An inspection and plan prominently label a pre-existing manifest as repository-supplied claimed state. Its validity and matching hashes do not prove who created it. Agent-guided planning does not use manifest presence as human authorization. The initial implementation retains ADR-0003 planning semantics but requires human review of any plan that uses repository-supplied claims to permit generated updates. Provenance attestations or local trust stores are deferred.
12. **Filesystem race protection remains best-effort against concurrent non-adversarial changes.** Plans bind root normalization, file types, hashes, executable modes, symlink state, and relevant manifest state. Apply retains no-follow path checks, immediate preflight revalidation, staging, backups, ordered replacement, and rollback. It does not claim safety against a malicious local actor with equivalent filesystem permissions or global atomicity across filesystem operations.

### Audit, hooks, and distribution

13. **Dry-run performs no filesystem or Git writes.** Inspection and dry-run plan artifacts are emitted to stdout only. Shell redirection is outside the command but must be explicit to the caller. Persistent audit storage, retention, permissions, signing, and redaction are deferred rather than weakening the current dry-run contract. Apply returns machine-readable result and rollback status without claiming approver authentication.
14. **Hooks do not perform bootstrap mutation.** Explicitly installed hooks may run deterministic validation or report drift, but they do not invoke an LLM, retrofit, merge, approve, or apply configuration automatically.
15. **Skill distribution is separate from the protocol guarantee.** The package includes canonical provider-neutral skill content and may generate a project-scoped maintenance skill after bootstrap. The initial architecture does not automatically install or own user-scoped skills. Pre-bootstrap users may load the packaged skill manually or use the CLI/out-of-band advisor fallback. Automated user-scope installation, upgrade, integrity, uninstall, and provider-specific discovery require a separate decision and verified platform contracts before support is claimed.

## Consequences

### Positive

- LLM judgment can improve evidence review, uncertainty handling, and user communication without becoming the trusted writer.
- Existing path safety, ownership, staging, rollback, and validation remain authoritative.
- Plan identifiers make reviewed content and preconditions reproducible without pretending to authenticate the reviewer.
- The CLI remains usable in CI, offline environments, and platforms without compatible skill execution.
- The initial implementation does not weaken unmanaged-file conflicts or dry-run guarantees.

### Negative

- The protocol, canonical plan identifier, bounded inspection, and skill add implementation complexity.
- The skill cannot autonomously finish apply without a verified host authorization channel; it must hand off to a human.
- The first release will not merge, adopt, overwrite, exempt, or continue past colliding unmanaged files. It will explain manual resolution and replan afterward while preserving the existing file.
- Provider-neutral skill content does not imply portable user-scoped installation.
- A repository-supplied manifest remains unauthenticated claimed state and needs prominent human review.

### Risks and mitigations

- **Prompt injection from repository content:** treat content as evidence, default to derived facts and hashes, bound and consent raw snippets, and keep writes behind deterministic planning and human handoff.
- **Typed-field semantic injection:** enforce a field authority matrix, explicit confirmation, contextual validation, normalization, and tests for Markdown, Unicode, delimiter, newline, and shell-like payloads.
- **Authorization confusion:** require trusted-terminal recomputation, complete deterministic display, and direct confirmation; reject `--yes` in agent-guided apply mode; do not describe legacy automation or an agent echoing a digest as human approval.
- **Legacy CLI downgrade:** document that unrestricted shell access is outside the protocol security boundary and retain explicit opt-in semantics for trusted direct callers.
- **Repository manifest provenance:** label it as an unauthenticated claim, bind it to the plan, and require human review before updates based on it.
- **Filesystem races:** preserve current confinement and stale-plan controls, bind file types and symlink state, and document the equal-permission adversary limitation.
- **Skill supply-chain risk:** ship canonical content with the package, avoid automatic user-scope installation, and require separate verified distribution decisions.
- **Scope expansion into merging:** keep preserve-unmanaged, semantic patches, and adoption outside this ADR and initial implementation.

## Implementation and validation

1. Define a threat model and strict schema-versioned inspection, intent, plan, and result models with canonical JSON serialization and field-level authority metadata.
2. Add bounded, no-follow, root-confined inspection and explicit raw-snippet consent controls.
3. Add a safe public facade that runs deterministic detection, rendering, validation, planning, apply, rollback, and target validation without accepting arbitrary generated content.
4. Add domain-separated plan identifiers that bind explicit target-root state, normalized output paths, ownership metadata, file types, modes, symlink state, and missing-state markers; reject stale, tampered, mismatched-target, mismatched-version, or changed-ownership apply attempts.
5. Add a read-only `inspect` command and agent-guided dry-run/expected-plan flags to `init` and `retrofit`, while preserving direct non-LLM workflows and exit codes.
6. Require the generated skill to stop at proposal/preview, and require the separate interactive human invocation to recompute and display the complete authoritative plan and obtain direct confirmation. Reject `--yes` in agent-guided apply mode.
7. Add canonical provider-neutral bootstrap/maintenance skill content without automatically installing user-scoped files.
8. Expand portable-content validation to all canonical skills and ensure diagnostics distinguish structural validity, ownership, and semantic trust.
9. Update architecture, workflow, platform support, generated-output evidence, examples, the MVP command-surface specification, and task tracking.
10. Add unit, integration, golden-tree, and platform contract tests for inspection confinement, truncation and consent, field authority, canonical replay, injection rejection, plan integrity, human handoff messaging, claimed manifest state, conflicts, stale state, file types, symlinks, rollback, idempotency, legacy CLI compatibility, and skill discovery.
11. Run repository validation, generated-project validation, all-platform dry-run, agent-guided init and retrofit fixtures through plan handoff, direct human-apply fixtures, and available platform diagnostics.

Implementation is gated on explicit human acceptance of this ADR. Release or version changes remain a separate confirmed activity under `docs/RELEASING.md`.

## Revisit triggers

- Supported hosts expose a verified, portable user-presence authorization channel.
- A portable standard emerges for agent skills, structured tool invocation, or project configuration ownership.
- Users require preserve-unmanaged, semantic merging, ownership adoption, or provenance attestations often enough to justify separate decisions.
- Plan integrity needs authenticated identities, expiration, single-use semantics, or multi-party authorization.
- The deterministic templates cannot represent important project-specific conventions through bounded typed fields.
- User-scoped skill distribution can be supported consistently with ownership, integrity, upgrade, and uninstall guarantees.

## References

- `docs/ARCHITECTURE.md`
- `docs/DEVELOPMENT_PROCESS.md`
- `docs/adr/0001-portable-core-and-platform-adapters.md`
- `docs/adr/0003-opt-in-integrations-and-safe-apply.md`
- `docs/PLATFORM_SUPPORT.md`
- `docs/superpowers-spec.md`
- `tasks/hybrid-agent-guided-bootstrap.md`
