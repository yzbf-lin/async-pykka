#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TARGET_DIR="${ROOT_DIR}/.benchmarks/pykka-repo"

mkdir -p "${ROOT_DIR}/.benchmarks"

if [ -d "${TARGET_DIR}/.git" ]; then
  echo "pykka repo already exists: ${TARGET_DIR}"
  git -C "${TARGET_DIR}" fetch --tags --prune
  git -C "${TARGET_DIR}" pull --ff-only
else
  git clone --depth 1 https://github.com/jodal/pykka.git "${TARGET_DIR}"
fi

echo "ready: ${TARGET_DIR}"
