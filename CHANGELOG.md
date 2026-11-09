# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- License switched from MIT to Apache-2.0.

## [0.2.0] - 2026-11-09

### Added

- Optional install-on-demand security-audit integration (ADR-0006): guidance mode during review, a scoped `quick`-profile release gate, and `standard`/`deep` audits at epic boundaries; renders `docs/SECURITY_AUDIT.md`.
- Optional install-on-demand task-breakdown and ticket skills (ADR-0007): step 2 planning with tracker-neutral task list targets; renders `docs/TASK_BREAKDOWN.md`.
- Process gates: pull requests for reviewable changes and pre-merge adversarial review (step 6), plus the security-audit release gate (step 7).
- Use-with-an-agent quickstart, upstream credits, and an MIT license (`LICENSE`, package metadata).

### Changed

- Development process mandates pull requests for all changes; direct pushes to the default branch are a process violation.
- Conditional ticket lifecycle section in the development process and a product-manager summary section in the task template.

## [0.1.0] - 2026-07-31

### Added

- Provider-neutral bootstrap CLI with `init`, `retrofit`, `inspect`, and `validate` commands.
- Native Claude Code, Codex, Pi, and OpenCode adapters.
- Progressive-disclosure documentation, ADR lifecycle, safe planning, ownership manifests, rollback, validation, examples, and cross-platform tests.
- Answers-file reference and a repository version-metadata synchronization helper.
- Optional agent-guided bounded inspection, strict typed proposals, deterministic plan-integrity identifiers, trusted-terminal human handoff, and a provider-neutral maintenance skill.

### Changed

- Expanded CLI help for safe noninteractive generation and retrofit flags.
- Added the read-only `inspect` command while preserving direct non-LLM initialization, retrofit, and validation workflows.

### Fixed

- Ignore Pi subagent runtime artifacts during unmanaged repository validation.
- Report missing ADR supersession references without validator tracebacks.
