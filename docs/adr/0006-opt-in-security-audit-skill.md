# ADR-0006: Opt-in security-audit skill integration

- **Status:** Proposed
- **Date:** 2026-11-09
- **Decision owners:** Not assigned
- **Scope:** Generator architecture and documentation architecture
- **Tags:** security, integrations, progressive-disclosure
- **Supersedes:** None
- **Superseded by:** None

## Context

The development process (`docs/DEVELOPMENT_PROCESS.md`) has no structured vulnerability-audit capability. Review (step 6) covers security only as part of diff review, and no workflow defines deep audits before releases or at epic boundaries.

Cloudflare publishes `security-audit-skill`, an agent-neutral six-phase audit workflow (reconnaissance, coverage-led hunting, candidate validation, structured findings, independent verification, target-neutral report) with guidance and full-audit modes. Integrating it requires deciding where it is invoked and how it is distributed, without violating ADR-0001 (portable core free of platform-specific content) or ADR-0003 (integrations are opt-in and writes are ownership-aware).

## Decision drivers

- The portable-core validator scans all rendered `.agents/skills/**` content against `PORTABLE_FORBIDDEN` tokens, including `Task tool`, which the upstream skill uses as its platform-agnostic delegation term. Verbatim vendoring into the portable core fails validation.
- The skill is large (17 files) and ships executable Node validators; vendoring third-party executables into every generated project adds manifest ownership and a supply-chain surface.
- Upstream evolves independently; generated projects must not pin stale audit guidance.
- Full audits spawn parallel sub-agents and require an OS-enforced sandbox; they are trigger-based, not per-change steps.
- Repository principle: hooks and CI workflows never invoke an LLM, so audits run in interactive agent sessions only.
- Generation must stay offline and deterministic; install-time network access is acceptable for an opt-in capability.

## Considered options

### Option 1: Vendor the skill verbatim into `.agents/skills/security-audit/`

Deterministic and offline, but fails the portable scan (`Task tool`), adds third-party executable content to the manifest, and burdens every upstream update with a re-vendor. Rejected.

### Option 2: Vendor a rewritten fork

Patching `Task tool` to neutral wording would pass the scan but forks upstream wording and drifts on every sync. Rejected.

### Option 3: Install-on-demand documentation (selected)

Generated projects receive documentation only; the skill is installed on demand with the skills CLI (`npx skills add https://github.com/cloudflare/security-audit-skill --skill security-audit`) or by copying `skills/security-audit/` into the platform skill directory when the CLI does not support it. The installed skill stays unmanaged, so ownership, manifests, and the portable scan are untouched.

### Option 4: Link only, no process wiring

Documents the skill but leaves triggers undefined; agents improvise when to run full audits. Rejected.

## Decision

Adopt Option 3 with tiered triggers:

1. Guidance mode for security questions during steps 1–6 and for security-sensitive reviews in step 6.
2. Full audit, `quick` profile, scoped to the diff between the last release ref and HEAD, as the release gate in step 7 when the release touches security-relevant surfaces.
3. Full audit, `standard` or `deep` profile, at epic or milestone boundaries; reruns are additive and target prior coverage gaps.

The generator renders `docs/SECURITY_AUDIT.md` as a mutable seed documenting install, modes, triggers, sandbox requirements, artifact policy (default output outside the repository; artifacts never committed), findings handling (confirmed findings enter step 2; boundary-changing findings require an ADR in step 3), and budget profiles. The skill is never generated, auto-installed, or manifest-owned.

## Consequences

### Positive

- No manifest ownership, no vendored executables, no portable-scan conflicts.
- Upstream audit guidance stays current at install time.
- Full-audit cost is explicit and trigger-based; guidance mode stays cheap.
- Safe degradation is preserved: without sandbox controls, findings remain `needs_validation`.

### Negative

- Install requires network access, Node.js, and CLI support for the platform; offline projects cannot use the skill without a manual copy.
- No version pin: upstream changes alter audit behavior between installs.
- Audit quality depends on the agent platform's parallel sub-agent support.

### Risks and mitigations

- Upstream wording or license changes: revisit triggers below; upstream is MIT-licensed.
- Accidental full-audit invocation on small tasks: the trigger table scopes full audits to explicit requests, release gates, and epic boundaries only.
- Audit artifacts leaking into the repository: default output is outside the target; in-repository output requires a version-control-ignored directory, and committing artifacts is prohibited.

## Implementation and validation

1. Added `docs/SECURITY_AUDIT.md` to the renderer core templates as a mutable seed.
2. Wired tiered triggers into the template and self-hosted `DEVELOPMENT_PROCESS.md`, indexed the document in both documentation indexes and the progressive-disclosure tiers, and added the optional-feature note to platform support.
3. Updated the golden all-platform tree and the generated-output catalog.
4. Gates: the unittest suite, `agentic_bootstrap validate --target .`, `docs-check`, and the canonical all-platform dry-run preview must pass.

## Revisit triggers

- Upstream publishes a portable-safe single-file variant: revisit vendoring (Option 1).
- The skills CLI drops support for a packaged platform, or a platform cannot receive the fallback copy: document the gap in `docs/PLATFORM_SUPPORT.md`.
- A project needs scheduled CI-driven audits: new design required, because workflows must not invoke LLMs.
- Upstream license changes away from MIT.

## References

- `docs/SECURITY_AUDIT.md` — self-hosted capability document; rendered project copy in the template
- `docs/DEVELOPMENT_PROCESS.md` — steps 6 and 7 triggers
- ADR-0001 — portable core and platform adapters
- ADR-0003 — opt-in integrations and safe apply
- https://github.com/cloudflare/security-audit-skill — upstream skill and workflow description
