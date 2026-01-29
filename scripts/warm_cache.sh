#!/bin/bash
# Pre-fetch mathlib cache for all SBS projects
# Run once before first build to avoid long compile times
#
# Usage: ./scripts/warm_cache.sh

set -e

SBS_ROOT="/Users/eric/GitHub/Side-By-Side-Blueprint"

echo "=== Warming mathlib cache for all projects ==="
echo "This fetches pre-compiled mathlib oleans (v4.27.0)"
echo ""

# Projects that use mathlib
PROJECTS=(
    "SBS-Test"
    "General_Crystallographic_Restriction"
    "PrimeNumberTheoremAnd"
)

for project in "${PROJECTS[@]}"; do
    PROJECT_PATH="$SBS_ROOT/$project"

    if [[ -d "$PROJECT_PATH" ]]; then
        echo "=== $project ==="
        cd "$PROJECT_PATH"
        lake exe cache get || echo "Warning: Cache fetch incomplete for $project"
        echo ""
    else
        echo "Skipping $project (not found at $PROJECT_PATH)"
    fi
done

echo "=== Cache warming complete ==="
echo "You can now run build_blueprint.sh without long mathlib compile times."
