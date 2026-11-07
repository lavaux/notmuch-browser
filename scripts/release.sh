#!/usr/bin/env bash
# Build the UI bundle, the wheel and the sdist, then check them. Never uploads anything.
set -euo pipefail
cd "$(dirname "$0")/.."

npm ci
npm run build
rm -rf dist
uv build
uv run python scripts/check_dist.py dist
# pkginfo 1.12.1 or newer is needed to read metadata version 2.5 (hatchling 1.27 and later).
uvx --with 'pkginfo>=1.12.1' twine check dist/*
echo
echo "Built and checked. Publish with: uv publish"
