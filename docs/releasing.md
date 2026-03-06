# Releasing async-pykka

Maintainer guide for publishing new versions to PyPI.

## Prerequisites

- PyPI project `async-pykka` already exists.
- GitHub repository: `yzbf-lin/async-pykka`.
- Workflow file exists: `.github/workflows/publish-pypi.yml`.
- GitHub environment `pypi` exists.
- PyPI Trusted Publisher is configured with:
  - Owner: `yzbf-lin`
  - Repository: `async-pykka`
  - Workflow: `publish-pypi.yml`
  - Environment: `pypi`

## Standard Release Flow (recommended)

1. Update version in `pyproject.toml`.
2. Run checks locally:

```bash
uv run ruff check .
uv run pytest -q
```

3. Commit and push to `main`:

```bash
git add pyproject.toml
git commit -m "chore: release vX.Y.Z"
git push origin main
```

4. Create and push a matching tag:

```bash
git tag vX.Y.Z
git push origin vX.Y.Z
```

5. Verify GitHub Actions `publish-pypi` succeeds.

Note: tag version must match `pyproject.toml` version exactly, e.g. `v0.1.5` <-> `0.1.5`.

## Local Fallback Publish (token-based)

If Actions publishing is unavailable:

```bash
export PYPI_TOKEN='pypi-xxxxx'
./scripts/publish_pypi.sh
unset PYPI_TOKEN
```

## Verify Published Package

```bash
uv pip install -U async-pykka
python - <<'PY'
import async_pykka
print(async_pykka.__version__ if hasattr(async_pykka, '__version__') else 'installed')
PY
```
