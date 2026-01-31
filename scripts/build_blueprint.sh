#!/bin/bash
# Shared Side-by-Side Blueprint build script
# Usage: ./scripts/build_blueprint.sh [project-directory]
#
# This script builds any SBS project using the pure Lean blueprint pipeline:
#   1. Cleans all toolchain and project build artifacts (eliminates stale caches)
#   2. Syncs all repos to GitHub
#   3. Builds toolchain (SubVerso -> LeanArchitect -> Dress -> Runway)
#   4. Fetches mathlib cache
#   5. Builds project with dressed artifacts
#   6. Generates dependency graph and site
#   7. Serves locally at http://localhost:8000
#
# Project configuration is auto-detected from runway.json (projectName field).

set -e

# Resolve project directory
if [[ -n "$1" ]]; then
    cd "$1"
fi
PROJECT_ROOT=$(pwd)

# Toolchain paths (hardcoded to local development structure)
SBS_ROOT="/Users/eric/GitHub/Side-By-Side-Blueprint"
SUBVERSO_PATH="$SBS_ROOT/subverso"
LEAN_ARCHITECT_PATH="$SBS_ROOT/LeanArchitect"
DRESS_PATH="$SBS_ROOT/Dress"
RUNWAY_PATH="$SBS_ROOT/Runway"
DRESS_BLUEPRINT_ACTION_PATH="$SBS_ROOT/dress-blueprint-action"

# Auto-detect project name from runway.json
if [[ ! -f "$PROJECT_ROOT/runway.json" ]]; then
    echo "ERROR: runway.json not found in $PROJECT_ROOT"
    exit 1
fi

PROJECT_NAME=$(grep -o '"projectName"[[:space:]]*:[[:space:]]*"[^"]*"' "$PROJECT_ROOT/runway.json" | sed 's/.*"\([^"]*\)".*/\1/')
if [[ -z "$PROJECT_NAME" ]]; then
    echo "ERROR: Could not extract projectName from runway.json"
    exit 1
fi

# Module name is same as project name
MODULE_NAME="$PROJECT_NAME"

echo "=== $PROJECT_NAME Blueprint Builder ==="
echo ""

# Check dependencies
check_dependency() {
    if ! command -v "$1" &> /dev/null; then
        echo "ERROR: $1 is not installed."
        echo "$2"
        exit 1
    fi
}

check_dependency "lake" "Please install Lean 4 and Lake."

# Verify local paths exist
for path in "$SUBVERSO_PATH" "$LEAN_ARCHITECT_PATH" "$DRESS_PATH" "$RUNWAY_PATH" "$DRESS_BLUEPRINT_ACTION_PATH"; do
    if [[ ! -d "$path" ]]; then
        echo "ERROR: Dependency not found at $path"
        exit 1
    fi
done

# Kill any existing processes on port 8000
echo "Killing any existing servers on port 8000..."
lsof -ti:8000 | xargs kill -9 2>/dev/null || true

echo ""
echo "=== Step 0: Syncing local repos to GitHub ==="

# Function to commit and push changes in a repo
commit_and_push() {
    local repo_path="$1"
    local repo_name="$(basename "$repo_path")"

    cd "$repo_path"

    # Check if there are any changes to commit
    if [[ -n $(git status --porcelain) ]]; then
        echo "  $repo_name: Committing changes..."
        git add -A
        git commit -m "Auto-commit from build_blueprint.sh

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
        echo "  $repo_name: Pushing..."
        git push
        echo "  $repo_name: Done."
    else
        echo "  $repo_name: No changes to commit"
    fi

    cd "$PROJECT_ROOT"
}

# Sync all repos
commit_and_push "$SUBVERSO_PATH"
commit_and_push "$LEAN_ARCHITECT_PATH"
commit_and_push "$DRESS_PATH"
commit_and_push "$RUNWAY_PATH"
commit_and_push "$DRESS_BLUEPRINT_ACTION_PATH"
commit_and_push "$PROJECT_ROOT"

echo ""
echo "=== Step 0b: Updating lake manifests ==="

# Update dependencies in order
echo "Updating LeanArchitect dependencies..."
(cd "$LEAN_ARCHITECT_PATH" && lake update SubVerso 2>/dev/null || true)

echo "Updating Dress dependencies..."
(cd "$DRESS_PATH" && lake update LeanArchitect 2>/dev/null || true)

echo "Updating Runway dependencies..."
(cd "$RUNWAY_PATH" && lake update Dress 2>/dev/null || true)

echo "Updating project dependencies..."
(cd "$PROJECT_ROOT" && lake update Dress 2>/dev/null || true)

# Commit and push any manifest changes
for repo_path in "$LEAN_ARCHITECT_PATH" "$DRESS_PATH" "$RUNWAY_PATH"; do
    repo_name=$(basename "$repo_path")
    cd "$repo_path"
    if [[ -n $(git status --porcelain lake-manifest.json 2>/dev/null) ]]; then
        echo "  Committing manifest update in $repo_name..."
        git add lake-manifest.json
        git commit -m "Update lake-manifest.json from build_blueprint.sh

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
        git push
    fi
    cd "$PROJECT_ROOT"
done

# Commit project manifest if changed
if [[ -n $(git status --porcelain lake-manifest.json 2>/dev/null) ]]; then
    echo "  Committing manifest update in project..."
    git add lake-manifest.json
    git commit -m "Update lake-manifest.json from build_blueprint.sh

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
    git push
fi

echo ""
echo "=== Step 1: Cleaning all build artifacts ==="

# Clean toolchain repos (eliminates stale caches)
echo "Cleaning toolchain build artifacts..."
rm -rf "$SUBVERSO_PATH/.lake/build"
rm -rf "$LEAN_ARCHITECT_PATH/.lake/build"
rm -rf "$DRESS_PATH/.lake/build"
rm -rf "$RUNWAY_PATH/.lake/build"

# Clean project artifacts
echo "Cleaning project build artifacts..."
rm -rf "$PROJECT_ROOT/.lake/build/lib/$MODULE_NAME"
rm -rf "$PROJECT_ROOT/.lake/build/ir/$MODULE_NAME"
rm -rf "$PROJECT_ROOT/.lake/build/dressed"
rm -rf "$PROJECT_ROOT/.lake/build/runway"

echo ""
echo "=== Step 2: Building local dependency forks ==="

# Build order: SubVerso -> LeanArchitect -> Dress -> Runway (respects dependency chain)

echo "Building SubVerso..."
(cd "$SUBVERSO_PATH" && lake build)

echo "Building LeanArchitect..."
(cd "$LEAN_ARCHITECT_PATH" && lake build)

echo "Building Dress..."
(cd "$DRESS_PATH" && lake build)

echo "Building Runway..."
(cd "$RUNWAY_PATH" && lake build)

echo ""
echo "=== Step 3: Fetching mathlib cache ==="
cd "$PROJECT_ROOT"
lake exe cache get || echo "Cache fetch completed (some files may have been skipped)"

echo ""
echo "=== Step 4: Building Lean project with dressed artifacts ==="
# Use BLUEPRINT_DRESS=1 environment variable to enable dressed artifact generation.
BLUEPRINT_DRESS=1 lake build

echo ""
echo "=== Step 5: Building blueprint facet ==="
lake build :blueprint

echo ""
echo "=== Step 6: Generating dependency graph ==="
# Run extract_blueprint graph command from local Dress
lake env "$DRESS_PATH/.lake/build/bin/extract_blueprint" graph \
    --build "$PROJECT_ROOT/.lake/build" \
    "$MODULE_NAME"

echo ""
echo "=== Step 7: Generating site with Runway ==="
OUTPUT_DIR="$PROJECT_ROOT/.lake/build/runway"

(cd "$RUNWAY_PATH" && lake exe runway \
    --build-dir "$PROJECT_ROOT/.lake/build" \
    --output "$OUTPUT_DIR" \
    build \
    "$PROJECT_ROOT/runway.json")

echo ""
echo "=== Step 8: Generating paper (if configured) ==="
# Check if paper.tex exists (either via runwayDir convention or explicit paperTexPath)
PAPER_EXISTS=false

# Check for runwayDir convention: runway/src/paper.tex
if grep -q '"runwayDir"' "$PROJECT_ROOT/runway.json"; then
    RUNWAY_DIR=$(grep -o '"runwayDir"[[:space:]]*:[[:space:]]*"[^"]*"' "$PROJECT_ROOT/runway.json" | sed 's/.*"\([^"]*\)".*/\1/')
    if [[ -f "$PROJECT_ROOT/$RUNWAY_DIR/src/paper.tex" ]]; then
        PAPER_EXISTS=true
    fi
fi

# Check for legacy paperTexPath
if grep -q '"paperTexPath"' "$PROJECT_ROOT/runway.json" && ! grep -q '"paperTexPath": null' "$PROJECT_ROOT/runway.json"; then
    PAPER_EXISTS=true
fi

if [[ "$PAPER_EXISTS" == "true" ]]; then
    (cd "$RUNWAY_PATH" && lake exe runway \
        --build-dir "$PROJECT_ROOT/.lake/build" \
        --output "$OUTPUT_DIR" \
        paper \
        "$PROJECT_ROOT/runway.json")
else
    echo "No paper.tex configured, skipping paper generation"
fi

echo ""
echo "=== Blueprint ready ==="
echo "  Output: $OUTPUT_DIR"
echo "  Web: http://localhost:8000"
echo ""

# Start server in background
python3 -m http.server -d "$OUTPUT_DIR" 8000 &
SERVER_PID=$!
echo "Server started (PID: $SERVER_PID)"

# Open browser
(sleep 1 && open "http://localhost:8000") &

echo ""
echo "=== BUILD COMPLETE ==="
echo "Server running at http://localhost:8000 (PID: $SERVER_PID)"
echo ""
