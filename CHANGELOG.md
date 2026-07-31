# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Answers-file reference and a repository version-metadata synchronization helper.

### Changed

- Expanded CLI help for safe noninteractive generation and retrofit flags.

### Fixed

- Ignore Pi subagent runtime artifacts during unmanaged repository validation.
- Report missing ADR supersession references without validator tracebacks.

## [0.1.0] - 2026-07-31

### Added

- Provider-neutral bootstrap CLI with `init`, `retrofit`, and `validate` commands.
- Native Claude Code, Codex, Pi, and OpenCode adapters.
- Progressive-disclosure documentation, ADR lifecycle, safe planning, ownership manifests, rollback, validation, examples, and cross-platform tests.
