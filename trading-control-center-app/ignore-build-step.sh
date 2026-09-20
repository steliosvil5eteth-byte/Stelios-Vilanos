#!/usr/bin/env bash
# Vercel Ignored Build Step for Trading Control Center.
# Exit 0 = skip deployment; exit 1 = continue deployment.
# Fail-safe: if Git history cannot be inspected, continue the build.

set -eu

if ! git rev-parse HEAD^ >/dev/null 2>&1; then
  echo "Parent commit unavailable; proceeding with Trading Control Center build."
  exit 1
fi

if git diff --quiet HEAD^ HEAD -- .; then
  echo "No Trading Control Center files changed; skipping this Vercel deployment."
  exit 0
fi

echo "Trading Control Center change detected; proceeding with Vercel deployment."
exit 1
