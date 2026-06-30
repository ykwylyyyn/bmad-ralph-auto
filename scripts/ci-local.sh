#!/usr/bin/env bash
# Reproduce CI quality gates locally (matches .github/workflows/ci.yml)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> Python tests"
pip install -q pyyaml
make test-all

echo "==> Rust formatting"
cargo fmt --all -- --check

echo "==> Rust build"
cargo build --workspace

echo "==> Rust clippy"
cargo clippy --workspace -- -D warnings

echo "==> Rust tests"
cargo test --workspace

echo "✅ All local CI checks passed"
