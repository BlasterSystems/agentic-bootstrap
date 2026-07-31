# Development Process

## 1. Understand

Read the request, relevant code, acceptance criteria, and minimum necessary documentation. Check `docs/adr/README.md` when architecture or rationale is involved.

## 2. Plan

Create or update a task file. Identify affected modules, tests, documentation, migration concerns, and whether an ADR is required. In agent-guided bootstrap workflows, the agent stops after preview and a human separately applies the recomputed plan.

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

Review correctness, security, compatibility, idempotency, rollback, docs, ADR indexing, and unsupported claims. Use independent read-only review for significant changes.

## 7. Complete

Meet all acceptance criteria, update support evidence, record test results, and report residual risks.

For a version bump or release, stop here and follow `docs/RELEASING.md` with the `semantic-versioning` skill. Release commits and tags require explicit confirmation.
