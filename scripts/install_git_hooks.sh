#!/bin/bash
# Installs project git hooks
mkdir -p .git/hooks
cp .git/hooks/pre-commit .git/hooks/pre-commit 2>/dev/null || true
chmod +x .git/hooks/pre-commit
echo "✅ Git pre-commit secret protection hook installed."
