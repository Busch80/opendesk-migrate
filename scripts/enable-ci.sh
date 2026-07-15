#!/usr/bin/env bash
# scripts/enable-ci.sh — Re-add GitHub Actions workflows after PAT scope is granted.
#
# Usage:
#   ./scripts/enable-ci.sh
#
# Requires:
#   1. GitHub admin grant the `workflow` scope to your PAT
#   2. Git remote `origin` configured

set -euo pipefail

echo "[enable-ci] Re-adding GitHub Actions workflow files..."
cd "$(dirname "$0")/.."

# Remove the ignore line that hides the workflows
sed -i '/^.github\/workflows\/$/{N;/GitHub Actions workflows/p}' .gitignore
sed -i '/^.github\/workflows\/$/d' .gitignore

git add -f .github/workflows/
git commit -m "ci: enable GitHub Actions (backend, frontend, docker)" || echo "Nothing to commit"
git push origin HEAD:main

echo ""
echo "[enable-ci] Done. CI should appear at:"
echo "  https://github.com/$(git remote get-url origin | sed 's/.*github.com[:/]//;s/\.git$//')/actions"
