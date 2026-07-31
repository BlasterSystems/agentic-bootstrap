# Releasing Agentic Bootstrap

Use the `semantic-versioning` skill for every version bump, release commit, and Git tag.

## Version policy

Agentic Bootstrap follows [Semantic Versioning 2.0.0](https://semver.org/). Tags are annotated and use `vMAJOR.MINOR.PATCH`.

Before `1.0.0`:

- `PATCH` is a backward-compatible fix or documentation correction.
- `MINOR` is a new capability or an intentional breaking change to the unstable API; breaking changes must be called out in the changelog.
- `1.0.0` requires explicit confirmation that the public CLI, generated layout, and manifest contract are stable.

After `1.0.0`, incompatible public behavior requires a major release.

## Authoritative version sources

These two files must contain the same version:

- `pyproject.toml`
- `src/agentic_bootstrap/__init__.py`

`src/agentic_bootstrap/manifest.py`, generated configurations, example manifests, CLI output, and platform documents derive their version from the package source. Refresh them; do not edit their version strings individually.

## Prepare a release

1. Require a clean worktree and inspect the latest `v*` tag.
2. Review user-visible changes and commits since that tag.
3. Propose a SemVer bump and obtain confirmation.
4. Update both authoritative version sources.
5. Move completed entries from `CHANGELOG.md` → `Unreleased` into `## [X.Y.Z] - YYYY-MM-DD`.
6. Refresh checked-in examples:

   ```bash
   scripts/agentic-bootstrap.sh init --platform pi --yes \
     --target examples/minimal --name minimal-example \
     --description "Portable core example"

   scripts/agentic-bootstrap.sh init --platform all --yes \
     --target examples/all-platforms --name all-platforms-example \
     --description "All adapters and optional integrations" \
     --mcp --agents --github --hooks
   ```

7. Run the release gate:

   ```bash
   PYTHONPATH=src python3 -m unittest discover -s tests -v
   PYTHONPATH=src python3 -m agentic_bootstrap validate --target .
   .agentic/bin/validate
   python3 -m pip wheel --no-deps --no-build-isolation -w /tmp/agentic-bootstrap-wheel .
   ```

8. Review the complete diff and obtain explicit confirmation before creating Git objects.
9. Create and verify the release:

   ```bash
   git commit -m "chore(release): vX.Y.Z"
   git tag -a "vX.Y.Z" -m "Release vX.Y.Z"
   git show --no-patch "vX.Y.Z"
   ```

## Publishing boundary

A local release ends with the annotated tag. Do not push the commit or tag and do not publish a wheel unless the user explicitly requests that separate action.
