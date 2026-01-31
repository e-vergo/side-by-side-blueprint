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
VERSO_PATH="$SBS_ROOT/verso"
GCR_PATH="$SBS_ROOT/General_Crystallographic_Restriction"
PNT_PATH="$SBS_ROOT/PrimeNumberTheoremAnd"

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

# Verify required local paths exist
for path in "$SUBVERSO_PATH" "$LEAN_ARCHITECT_PATH" "$DRESS_PATH" "$RUNWAY_PATH" "$VERSO_PATH" "$DRESS_BLUEPRINT_ACTION_PATH"; do
    if [[ ! -d "$path" ]]; then
        echo "ERROR: Required dependency not found at $path"
        exit 1
    fi
done

# Warn about optional paths
for path in "$GCR_PATH" "$PNT_PATH"; do
    if [[ ! -d "$path" ]]; then
        echo "Warning: Showcase project not found at $path (skipping)"
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

    # Skip if path doesn't exist
    if [[ ! -d "$repo_path" ]]; then
        echo "  $repo_name: Skipped (not found)"
        return 0
    fi

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

# Sync toolchain repos
commit_and_push "$SUBVERSO_PATH"
commit_and_push "$LEAN_ARCHITECT_PATH"
commit_and_push "$DRESS_PATH"
commit_and_push "$RUNWAY_PATH"

# Sync Verso fork
commit_and_push "$VERSO_PATH"

# Sync CI action
commit_and_push "$DRESS_BLUEPRINT_ACTION_PATH"

# Sync showcase projects
commit_and_push "$GCR_PATH"
commit_and_push "$PNT_PATH"

# Sync parent monorepo (SBS root)
commit_and_push "$SBS_ROOT"

# Sync current project
commit_and_push "$PROJECT_ROOT"

echo ""
echo "=== Step 0a: Pulling latest from GitHub ==="

pull_latest() {
    local repo_path="$1"
    local repo_name="$(basename "$repo_path")"

    # Skip if path doesn't exist
    if [[ ! -d "$repo_path" ]]; then
        echo "  $repo_name: Skipped (not found)"
        return 0
    fi

    cd "$repo_path"
    echo "  $repo_name: Pulling latest..."
    git pull --rebase || git pull
    cd "$PROJECT_ROOT"
}

# Pull all repos
pull_latest "$SUBVERSO_PATH"
pull_latest "$LEAN_ARCHITECT_PATH"
pull_latest "$DRESS_PATH"
pull_latest "$RUNWAY_PATH"
pull_latest "$VERSO_PATH"
pull_latest "$DRESS_BLUEPRINT_ACTION_PATH"
pull_latest "$GCR_PATH"
pull_latest "$PNT_PATH"
pull_latest "$SBS_ROOT"
pull_latest "$PROJECT_ROOT"

echo ""
echo "=== Step 0b: Updating lake manifests ==="

# Update dependencies in order
echo "Updating LeanArchitect dependencies..."
(cd "$LEAN_ARCHITECT_PATH" && lake update SubVerso 2>/dev/null || true)

echo "Updating Dress dependencies..."
(cd "$DRESS_PATH" && lake update LeanArchitect 2>/dev/null || true)

echo "Updating Runway dependencies..."
(cd "$RUNWAY_PATH" && lake update Dress 2>/dev/null || true)

echo "Updating Verso dependencies..."
(cd "$VERSO_PATH" && lake update 2>/dev/null || true)

echo "Updating GCR dependencies..."
if [[ -d "$GCR_PATH" ]]; then
    (cd "$GCR_PATH" && lake update Dress 2>/dev/null || true)
fi

echo "Updating PNT dependencies..."
if [[ -d "$PNT_PATH" ]]; then
    (cd "$PNT_PATH" && lake update Dress 2>/dev/null || true)
fi

echo "Updating project dependencies..."
(cd "$PROJECT_ROOT" && lake update Dress 2>/dev/null || true)

# Commit and push any manifest changes
for repo_path in "$LEAN_ARCHITECT_PATH" "$DRESS_PATH" "$RUNWAY_PATH" "$VERSO_PATH" "$GCR_PATH" "$PNT_PATH"; do
    # Skip if path doesn't exist
    if [[ ! -d "$repo_path" ]]; then
        continue
    fi
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
echo "=== Step 5b: Building Verso documents ==="
if [[ -f "$PROJECT_ROOT/$MODULE_NAME/Blueprint.lean" ]]; then
    echo "Building $MODULE_NAME.Blueprint..."
    lake build "$MODULE_NAME.Blueprint"
else
    echo "No Blueprint.lean found, skipping"
fi
if [[ -f "$PROJECT_ROOT/$MODULE_NAME/Paper.lean" ]]; then
    echo "Building $MODULE_NAME.Paper..."
    lake build "$MODULE_NAME.Paper"
else
    echo "No Paper.lean found, skipping"
fi

echo ""
echo "=== Step 5c: Generating Verso HTML ==="
VERSO_OUTPUT_DIR="$PROJECT_ROOT/.lake/build/runway"
mkdir -p "$VERSO_OUTPUT_DIR"

if [[ -f "$PROJECT_ROOT/$MODULE_NAME/Blueprint.lean" ]]; then
    if lake exe generate-blueprint-verso --help &>/dev/null 2>&1 || lake exe generate-blueprint-verso &>/dev/null 2>&1; then
        echo "Generating Verso blueprint HTML..."
        lake exe generate-blueprint-verso || echo "Warning: Verso blueprint generation failed (feature may not be implemented yet)"
    else
        echo "No generate-blueprint-verso executable found, skipping"
    fi
else
    echo "No Blueprint.lean found, skipping Verso blueprint HTML"
fi

if [[ -f "$PROJECT_ROOT/$MODULE_NAME/Paper.lean" ]]; then
    if lake exe generate-paper-verso --help &>/dev/null 2>&1 || lake exe generate-paper-verso &>/dev/null 2>&1; then
        echo "Generating Verso paper HTML..."
        lake exe generate-paper-verso || echo "Warning: Verso paper generation failed (feature may not be implemented yet)"
    else
        echo "No generate-paper-verso executable found, skipping"
    fi
else
    echo "No Paper.lean found, skipping Verso paper HTML"
fi

echo ""
echo "=== Step 5d: Generating Verso PDF ==="
if [[ -f "$PROJECT_ROOT/$MODULE_NAME/Paper.lean" ]]; then
    # Detect available TeX compiler (try in order of preference)
    VERSO_TEX_CMD=""
    if command -v lualatex &> /dev/null; then
        VERSO_TEX_CMD="lualatex"
    elif command -v pdflatex &> /dev/null; then
        VERSO_TEX_CMD="pdflatex"
    elif command -v xelatex &> /dev/null; then
        VERSO_TEX_CMD="xelatex"
    fi

    if [[ -z "$VERSO_TEX_CMD" ]]; then
        echo "Warning: No LaTeX compiler found (tried lualatex, pdflatex, xelatex), skipping Verso PDF generation"
    else
        # Try to generate TeX output
        if lake exe generate-paper-verso --help &>/dev/null 2>&1 || lake exe generate-paper-verso &>/dev/null 2>&1; then
            echo "Generating Verso paper TeX..."
            mkdir -p "$VERSO_OUTPUT_DIR/tex"
            lake exe generate-paper-verso --with-tex --tex-output "$VERSO_OUTPUT_DIR/tex" || echo "Warning: Verso TeX generation failed"

            if [[ -f "$VERSO_OUTPUT_DIR/tex/paper_verso.tex" ]]; then
                echo "Compiling Verso PDF with $VERSO_TEX_CMD..."
                pushd "$VERSO_OUTPUT_DIR/tex" > /dev/null
                $VERSO_TEX_CMD -interaction=nonstopmode paper_verso.tex || true
                $VERSO_TEX_CMD -interaction=nonstopmode paper_verso.tex || true
                $VERSO_TEX_CMD -interaction=nonstopmode paper_verso.tex || true
                popd > /dev/null

                if [[ -f "$VERSO_OUTPUT_DIR/tex/paper_verso.pdf" ]]; then
                    mv "$VERSO_OUTPUT_DIR/tex/paper_verso.pdf" "$VERSO_OUTPUT_DIR/"
                    echo "Verso PDF generated: $VERSO_OUTPUT_DIR/paper_verso.pdf"
                else
                    echo "Warning: $VERSO_TEX_CMD did not produce a PDF"
                fi
            else
                echo "No paper_verso.tex generated, skipping PDF compilation"
            fi
        else
            echo "No generate-paper-verso executable found, skipping Verso PDF"
        fi
    fi
else
    echo "No Paper.lean found, skipping Verso PDF"
fi

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
echo "=== Final: Syncing any remaining changes ==="
commit_and_push "$PROJECT_ROOT"

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
