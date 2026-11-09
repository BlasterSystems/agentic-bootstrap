# Development Process

## 1. Understand

Read the request, relevant code, acceptance criteria, and minimum necessary documentation. Check `docs/adr/README.md` when architecture or rationale is involved.

## 2. Plan

Create or update a task file. Identify affected modules, tests, documentation, migration concerns, and whether an ADR is required. In agent-guided bootstrap workflows, the agent stops after preview and a human separately applies the recomputed plan.

For multi-step or ambiguous work, use the planning-and-task-breakdown skill; the task list target and tracker mapping are defined in `docs/TASK_BREAKDOWN.md`.

## 3. Decide

Use an ADR for durable, cross-cutting, security-sensitive, data, deployment, dependency, or integration choices. Create it as Proposed, compare real alternatives, and obtain human approval before Accepted.

## 4. Implement

Keep one writer for overlapping files. Preserve unmanaged files. Render JSON/TOML structurally. Keep the portable core free of provider-specific syntax and make integrations opt-in.

## 5. Validate

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m agentic_bootstrap validate --target .
```

When adapters change, generate temporary fixtures and run platform contract diagnostics where available.

## 6. Review

Review correctness, security, compatibility, idempotency, rollback, docs, ADR indexing, and unsupported claims. Open a pull request for reviewable changes. Before merge, significant changes require an independent adversarial review: a fresh read-only pass that tries to disprove correctness, security, compatibility, and scope claims.

For security-sensitive changes or open vulnerability questions, use the security-audit skill in guidance mode (`docs/SECURITY_AUDIT.md`).

## 7. Complete

Meet all acceptance criteria, update support evidence, record test results, and report residual risks. Before tagging a release that touches security-relevant surfaces, run the scoped release-gate audit described in `docs/SECURITY_AUDIT.md`.

For a version bump or release, stop here and follow `docs/RELEASING.md` with the `semantic-versioning` skill. Release commits and tags require explicit confirmation.
