#!/usr/bin/env bash
# One-time project setup. Safe to run again.
set -euo pipefail

for tool in uv pnpm docker gitleaks pre-commit; do
  if ! command -v "$tool" >/dev/null; then
    echo "Missing tool: $tool. See docs/guides/getting-started.md"
    exit 1
  fi
done

python3 scripts/sync_env.py

(cd apps/api && uv sync)
(cd apps/web && pnpm install)
pre-commit install

echo "Setup finished. Run: make up"
