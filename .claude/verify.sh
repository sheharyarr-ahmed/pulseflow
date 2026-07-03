#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
git diff --quiet && git diff --cached --quiet && exit 0
[ "$(git config core.hooksPath || true)" = ".githooks" ] || { echo "BLOCK: run: git config core.hooksPath .githooks" >&2; exit 2; }
.venv/bin/pytest -q
