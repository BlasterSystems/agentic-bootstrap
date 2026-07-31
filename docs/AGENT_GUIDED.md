# Agent-Guided Bootstrap Protocol

The agent-guided workflow adds LLM assistance without making the LLM a trusted writer. ADR-0005 defines the normative trust and authorization boundary.

## Roles

- **Inspector:** reads bounded regular UTF-8 files without following symlinks, executing project commands, using network access, or including known secret locations.
- **Agent:** reviews untrusted evidence, asks questions, and may produce a strict typed proposal. It cannot confirm facts or authorize features.
- **Deterministic core:** validates typed values, renders canonical output, computes ownership-aware operations and a plan identifier, applies through staging, and validates the result.
- **Human:** reviews the trusted-terminal recomputation and directly confirms apply.

## Inspect

```bash
agentic-bootstrap inspect --target /path/to/project
```

The JSON artifact reports evidence paths, hashes, confidence, exclusions, file/byte/entry/depth limits, and truncation. Raw snippets are omitted by default. `--include-snippets` requires an explicit decision because repository text may be sent to a remote model provider.

Inspection artifacts are evidence, not authorization. The scanner cannot restrict additional repository access already granted to the surrounding agent runtime.

## Typed proposal

An optional proposal uses `agentic-bootstrap-intent/v1`:

```json
{
  "schema": "agentic-bootstrap-intent/v1",
  "project": {
    "name": "example-service",
    "test_command": "python -m unittest"
  },
  "features": {
    "platforms": ["pi"],
    "mcp": false,
    "agents": false,
    "github": false,
    "scheduled_audit": false,
    "hooks": false
  }
}
```

The artifact is an unverified proposal. Unknown fields and arbitrary paths, content, patches, credentials, modes, ownership metadata, confirmations, and approvals are rejected.

## Preview and handoff

```bash
agentic-bootstrap retrofit \
  --agent-guided \
  --agent-intent /outside/project/intent.json \
  --dry-run \
  --plan-format json \
  --target /path/to/project
```

Preview writes only to stdout. Existing repository file contents are withheld from the agent preview; update and removal entries expose hashes and require exact diff review in the trusted terminal. The plan identifier binds the normalized request, target-root state, desired paths and hashes, modes, mutability and resulting ownership, current destination state, operations, and removal policy. It provides integrity only, not identity or authorization.

The agent must stop after showing the preview. A human then runs the corresponding command separately in an interactive trusted terminal:

```bash
agentic-bootstrap retrofit \
  --agent-guided \
  --agent-intent /outside/project/intent.json \
  --expected-plan PLAN_SHA256 \
  --target /path/to/project
```

The deterministic command asks the human to confirm facts and sensitive features, recomputes and displays the complete authoritative plan and terminal-safe exact diffs, verifies the expected identifier, and asks for final confirmation. Apply and post-apply validation return a schema-versioned deterministic result with rollback status. `--yes` is rejected in agent-guided mode.

## Embedding facade

Trusted applications may import `inspect_project`, `prepare_bootstrap`, and `apply_bootstrap` from `agentic_bootstrap`. The facade accepts typed bootstrap requests only and does not accept desired-file maps. `apply_bootstrap` returns a schema-versioned result containing status, errors, and rollback status rather than treating a public plan identifier as authorization. An untrusted agent must not call the apply facade; the initial agent workflow uses the interactive CLI handoff.

## Boundaries

- Unmanaged conflicts still abort without overwrite, adoption, exemption, or merge.
- Existing manifests are labeled repository-supplied unauthenticated ownership claims.
- MCP, specialized agents, workflows, schedules, hooks, and obsolete removal remain explicitly selected.
- Hooks never perform LLM inspection or bootstrap mutation.
- Direct non-LLM CLI automation remains available as a separate trusted-caller workflow.
- Automatic user-scope skill installation, semantic merging, authenticated approvals, and protection from an equal-permission local adversary are not provided.
