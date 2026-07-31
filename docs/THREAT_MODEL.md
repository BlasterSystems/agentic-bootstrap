# Agent-Guided Threat Model

## Assets

- User-owned destination files and Git configuration
- Generated-file ownership metadata and rollback state
- Project secrets and private source text
- Human control of integrations, removals, and apply
- Integrity of the reviewed request and plan

## Trust boundaries

- Repository content, inspection artifacts, agent proposals, and repository-supplied manifests are untrusted.
- The deterministic renderer, serializers, planner, confinement checks, staged apply, and validators are trusted project components.
- A separately invoked interactive terminal is the initial user-presence boundary for agent-guided apply.
- Direct CLI automation is a separate trusted-caller mode.
- Coding-platform permissions and any shell access already granted to an agent are external boundaries.

## Covered threats

- Path traversal and symlink destination escapes
- Secret, binary, special-file, vendor, VCS, and generated-tree inclusion in bounded inspection
- Unbounded inspection volume and implicit raw snippet disclosure
- Arbitrary LLM paths, content, patches, modes, credentials, ownership metadata, confirmations, or approvals
- Silent integration enablement and unmanaged-file overwrite
- Plan tampering and stale target, manifest, content, type, mode, symlink, or ownership state
- Apply failure through staged writes, backups, rollback, and post-apply validation

## Explicit limitations

- The plan identifier is a public integrity digest, not an authenticated or one-time approval.
- A repository manifest is an unauthenticated ownership claim.
- Structural and syntax validation do not prove semantic safety.
- The scanner cannot restrict reads independently granted by an agent host.
- Filesystem operations are not globally atomic and do not defend against a malicious actor with equivalent filesystem permissions.
- User-scope skill distribution, semantic merge, ownership adoption, and authenticated approvals are deferred.
