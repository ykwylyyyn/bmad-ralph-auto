#!/usr/bin/env bash
# Reproduce CI quality gates locally (matches .github/workflows/ci.yml)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> Python tests"
pip install -q pyyaml
make test-all

echo "✅ All local CI checks passed"
