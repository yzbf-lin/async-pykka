#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

if [[ -z "${PYPI_TOKEN:-}" ]]; then
  echo "PYPI_TOKEN is not set."
  echo "Example: export PYPI_TOKEN='pypi-xxxxx'"
  echo "Then run: ./scripts/publish_pypi.sh"
  exit 1
fi

uv build
uvx --from twine twine upload -u __token__ -p "$PYPI_TOKEN" dist/*

echo "Publish completed."
