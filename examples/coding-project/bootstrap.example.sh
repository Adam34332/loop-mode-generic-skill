#!/usr/bin/env bash
set -euo pipefail

# Example bootstrap check. Adapt it to your repo before use.
# Keep this safe: no production migrations, no deletes, no dependency upgrades.

if [ -f package.json ]; then
  npm install
  npm run lint --if-present
  npm run build --if-present
elif [ -f pyproject.toml ] || [ -f pytest.ini ]; then
  python3 -m pytest --collect-only >/tmp/loop-mode-pytest-collect.txt
else
  echo "No known bootstrap checks found; add project-specific checks." >&2
fi

echo "BOOTSTRAP_CHECK_OK"
