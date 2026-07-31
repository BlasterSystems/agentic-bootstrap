# Answers File

Use `--answers FILE` to provide confirmed project facts and feature choices without repeating every CLI flag. CLI flags override values from the file; detector evidence supplies fields that remain absent.

## Example

```json
{
  "project": {
    "name": "example-service",
    "description": "Processes example requests",
    "build_command": "python3 -m build",
    "test_command": "python3 -m unittest discover -s tests -v",
    "run_command": "python3 -m example_service",
    "ticket_prefix": null
  },
  "features": {
    "platforms": ["claude", "codex", "pi", "opencode"],
    "mcp": false,
    "agents": false,
    "github": true,
    "scheduled_audit": false,
    "hooks": false
  }
}
```

`features.platforms` may also be the string `"all"` or a comma-separated string such as `"claude,codex"`. Feature values must be JSON booleans, not strings. Project command fields and `ticket_prefix` accept a string or `null`.

Preview before applying:

```bash
agentic-bootstrap init --answers answers.json --dry-run --yes --target /path/to/project
```

Keep answers files free of credentials. They describe project metadata and generated features, not secrets or provider tokens.
