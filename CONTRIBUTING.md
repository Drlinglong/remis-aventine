# Contributing to Aventine

Aventine is pre-alpha. Small, testable changes are easier to review than broad framework rewrites.

## Development setup

```bash
python -m venv .venv
python -m pip install -e ".[dev]"
ruff check .
ruff format --check .
pytest --cov
python -m build
```

## Contribution rules

- Keep the core provider-neutral and project-neutral.
- Preserve the hard-validator veto boundary.
- Add or update tests for schema, aggregation, parser, and policy changes.
- Treat judge output as untrusted structured input.
- Do not add external benchmark corpora, model weights, generated benchmark results, or secrets.
- Record the source, version, license, and citation requirements for every external adapter.
- Avoid tests that require a real provider, a large download, or an expensive model run.

## Pull requests

Describe the behavior being changed, the trust boundary it affects, and the commands used to verify
the change. If a schema changes, explain compatibility and increment its `schema_version` when the
change is breaking.

By contributing, you agree that your contribution is licensed under the repository's AGPL-3.0-only
license unless a file explicitly states otherwise.
