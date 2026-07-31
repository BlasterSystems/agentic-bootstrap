# Agentic Bootstrap

Bootstrap greenfield or existing projects with provider-neutral instructions for Claude Code, Codex, Pi, and OpenCode. Integrations and privileged behavior remain opt-in.

## Quick start

Requires Python 3.11+.

Clone or download this repository, then run from its checkout:

```bash
cd agentic-bootstrap
python3 -m pip install -e .

# Preview an all-platform project without writing files
agentic-bootstrap init --platform all --dry-run --yes --target /path/to/project

# Initialize a minimal Pi-compatible project
agentic-bootstrap init --platform pi --yes --target /path/to/project

# Add the portable core and selected adapters to an existing project
agentic-bootstrap retrofit --platform claude,codex,pi,opencode \
  --dry-run --yes --target /path/to/project

# Inspect bounded evidence without changing the project
agentic-bootstrap inspect --target /path/to/project

# Validate generated configuration
agentic-bootstrap validate --target /path/to/project
```

The repository-local entry point works without installation:

```bash
scripts/agentic-bootstrap.sh init --platform all --dry-run --yes --target /path/to/project
```

## Optional features

```text
--mcp              Native MCP configuration where supported
--agents           Specialized-agent definitions where supported
--github           GitHub documentation-check workflow
--scheduled-audit  Weekly docs-check schedule; implies --github
--hooks            Git hooks without changing Git configuration
--answers FILE     Confirmed project and feature answers as JSON
--agent-guided     LLM-advisory preview with separate human apply
--agent-intent FILE Strict unverified proposal for agent-guided mode
--expected-plan ID Integrity check for interactive human apply
--plan-format json Machine-readable plan
--remove-obsolete  Explicitly remove obsolete manifest-owned files
```

See the [answers-file reference](docs/ANSWERS.md) for trusted-caller JSON and the [agent-guided protocol](docs/AGENT_GUIDED.md) for bounded inspection, typed proposals, preview, and trusted-terminal handoff. Unmanaged files are never overwritten; start with `--dry-run` when retrofitting.

## Documentation: load progressively

Read only what the current task requires:

1. **Start here:** [documentation index](docs/README.md)
2. **Contributing:** [development process](docs/DEVELOPMENT_PROCESS.md)
3. **Architecture:** [architecture overview](docs/ARCHITECTURE.md), then the [ADR index](docs/adr/README.md) before individual decisions
4. **Platform details:** [support matrix](docs/PLATFORM_SUPPORT.md)
5. **Generated files:** [exact all-feature output](docs/GENERATED_OUTPUT.md)
6. **Releases:** [Semantic Versioning and Git tags](docs/RELEASING.md)
7. **Knowledge strategy:** [LLM Wiki evaluation and pilot plan](docs/LLM_WIKI_EVALUATION.md)

## Development

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m agentic_bootstrap validate --target .
```
