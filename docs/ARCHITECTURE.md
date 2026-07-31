# Architecture

## Overview

Agentic Bootstrap separates portable project knowledge, coding-platform adapters, and optional integrations.

```text
confirmed answers + detector evidence
                 |
                 v
typed project model
                 |
                 v
portable renderer ──> platform adapters ──> optional integrations
                 |
                 v
create/update/skip/conflict plan
                 |
                 v
validated staged output ──> rollback-capable apply ──> ownership manifest
```

## Modules

- `model.py`: typed facts, features, and generated files
- `detection.py`: evidence-based stack and command detection
- `renderer.py`: portable core composition
- `adapters/`: Claude, Codex, Pi, and OpenCode native artifacts
- `planner.py`: ownership-aware file operation planning
- `apply.py`: staged apply and rollback
- `manifest.py`: generated-file hashes and adapter selection
- `validation.py`: syntax, token, portable-core, and ADR checks
- `cli.py`: init, retrofit, and validate commands

## Safety model

Unmanaged files are never overwritten. Immutable manifest-owned files update only when their content and mode match the prior generated state; drift becomes a conflict. Explicitly marked mutable seeds—project instructions, architecture/process docs, ADR index/template, and task template—may be customized and are preserved while their structure is validated. Dry-run does not create the target or modify Git configuration.

Git hooks are generated only when selected, and `setup-hooks.sh` refuses to replace an existing custom `core.hooksPath` without `--force`.

## Portable core

`AGENTS.md`, workflow documents, tasks, ADRs, validators, and `.agents/skills` contain no coding-platform tool syntax. Adapters add only officially supported platform files.

## Architecture decisions

See `docs/adr/README.md`. Read the index before loading individual records.
