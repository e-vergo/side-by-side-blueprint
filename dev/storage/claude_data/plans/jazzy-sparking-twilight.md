# Monorepo Follow-up: Storage Move & Build Scripts

## Goal

Three follow-up changes to the monorepo refactor:
1. Move storage submodule from root to dev/storage
2. Clean up storage folder (consolidate GCR duplicates)
3. Add one-click build scripts for each project

## Target Structure (Updated)

```
Side-By-Side-Blueprint/
├── CLAUDE.md
├── pyproject.toml
├── .gitignore
├── .gitmodules
├── .claude/
│
├── forks/                              (submodules)
├── toolchain/                          (submodules)
├── showcase/                           (submodules)
│
└── dev/
    ├── build-sbs-test.sh              # NEW: One-click SBS-Test
    ├── build-gcr.sh                   # NEW: One-click GCR
    ├── build-pnt.sh                   # NEW: One-click PNT
    ├── scripts/
    │   └── sbs/
    ├── .refs/
    ├── markdowns/
    └── storage/                        # MOVED from root
        ├── README.md
        ├── unified_ledger.json
        ├── archive_index.json
        ├── compliance_ledger.json
        ├── SBSTest/
        ├── GCR/                        # CONSOLIDATED (was GCR + GeneralCrystallographicRestriction)
        ├── PNT/
        ├── rubrics/
        ├── charts/
        ├── caches/
        └── mathlib-pins/
```

---

## Task 1: Move Storage Submodule to dev/storage

**Rationale:** Consolidate all dev tooling under dev/ for cleaner root.

### Steps

1. **Update .gitmodules**
   ```
   # Change path from "storage" to "dev/storage"
   [submodule "dev/storage"]
       path = dev/storage
       url = https://github.com/e-vergo/sbs-storage.git
   ```

2. **Git submodule operations**
   ```bash
   git submodule deinit storage
   git rm storage
   git submodule add https://github.com/e-vergo/sbs-storage.git dev/storage
   ```

3. **Update Python path constants**
   - `dev/scripts/sbs/utils.py`: `ARCHIVE_DIR = SBS_ROOT / "dev" / "storage"`
   - `dev/scripts/build.py`: Update all `storage/` references

4. **Update documentation paths**
   - CLAUDE.md: `storage/` → `dev/storage/`
   - Skills files: update archive paths

---

## Task 2: Clean Up Storage (Consolidate GCR Duplicates)

**Finding:** Two directories exist with overlapping content:
- `GCR/` - Legacy (just metadata, 1 screenshot)
- `GeneralCrystallographicRestriction/` - Full captures (4 files)

**Decision:** Consolidate to `GCR/` as canonical name (matches project shorthand).

### Steps

1. **In sbs-storage repo:**
   ```bash
   # Merge content: keep fuller data
   cp -r GeneralCrystallographicRestriction/latest/* GCR/latest/
   rm -rf GeneralCrystallographicRestriction/
   ```

2. **Update archive_index.json**
   - Find entries with `"project": "GeneralCrystallographicRestriction"` or `"Crystallographic"`
   - Normalize to `"project": "GCR"`

3. **Add PNT directory** (for consistency)
   ```bash
   mkdir -p PNT/latest PNT/archive
   ```

4. **Commit and push sbs-storage**

---

## Task 3: Create One-Click Build Scripts

**Location:** `/Users/eric/GitHub/Side-By-Side-Blueprint/dev/`

### Script Template

Each script does:
1. Navigate to project directory
2. Run build.py with --capture flag
3. Print summary (URL, timing, archive entry)

### dev/build-sbs-test.sh
```bash
#!/bin/bash
set -e
cd "$(dirname "$0")/../toolchain/SBS-Test"
python ../../dev/scripts/build.py --capture "$@"
```

### dev/build-gcr.sh
```bash
#!/bin/bash
set -e
cd "$(dirname "$0")/../showcase/General_Crystallographic_Restriction"
python ../../dev/scripts/build.py --capture "$@"
```

### dev/build-pnt.sh
```bash
#!/bin/bash
set -e
cd "$(dirname "$0")/../showcase/PrimeNumberTheoremAnd"
python ../../dev/scripts/build.py --capture "$@"
```

### Usage
```bash
./dev/build-sbs-test.sh           # Full build + capture
./dev/build-sbs-test.sh --dry-run # Preview only
./dev/build-gcr.sh --skip-cache   # Force rebuild
```

---

## Verification

1. `git submodule status` shows dev/storage (not storage)
2. `python -m sbs --help` works (paths resolve correctly)
3. `./dev/build-sbs-test.sh --dry-run` succeeds
4. Storage contains: SBSTest/, GCR/, PNT/ (no GeneralCrystallographicRestriction)

---

## Files Modified

| File | Changes |
|------|---------|
| `.gitmodules` | storage → dev/storage |
| `dev/scripts/sbs/utils.py` | Update ARCHIVE_DIR |
| `dev/scripts/build.py` | Update storage paths |
| `CLAUDE.md` | Update storage references |
| `.claude/skills/*.md` | Update archive paths |
| `dev/storage/` | Consolidate GCR, add PNT |
| `dev/build-*.sh` | NEW: 3 build scripts |

---

# ARCHIVED: Original Monorepo Refactor Plan (Completed)

## Execution Phases (COMPLETED)
   - `ARCHITECTURE.md` → `dev/markdowns/ARCHITECTURE.md`
   - `GOALS.md` → `dev/markdowns/GOALS.md`
   - `README.md` → `dev/markdowns/README.md`
3. Delete vestigial content:
   - `rm -rf reference-manual/`
   - `rm LICENSE`
4. Create `pyproject.toml` at root (pointing to `dev/scripts/sbs/`)

### Phase 3: Submodule Conversion

**Agent 4: Convert repos to submodules**

This is the critical phase. Order matters.

1. **Update .gitignore** - Remove all repo ignore entries
2. **Move repos to temp** - Preserve local state in `/tmp/sbs-migration/`
3. **Add submodules at new paths:**
   ```
   forks/LeanArchitect      ← https://github.com/e-vergo/LeanArchitect.git
   forks/subverso           ← https://github.com/e-vergo/subverso.git
   forks/verso              ← https://github.com/e-vergo/verso.git
   toolchain/Dress          ← https://github.com/e-vergo/Dress.git
   toolchain/Runway         ← https://github.com/e-vergo/Runway.git
   toolchain/SBS-Test       ← https://github.com/e-vergo/SBS-Test.git
   toolchain/dress-blueprint-action ← https://github.com/e-vergo/dress-blueprint-action.git
   showcase/General_Crystallographic_Restriction ← ...
   showcase/PrimeNumberTheoremAnd ← ...
   storage/                 ← https://github.com/e-vergo/sbs-storage.git
   ```
4. **Verify** - `git submodule status` shows all 10 submodules

### Phase 4: Path Reference Updates

**Agent 5: Update all hardcoded paths**

Critical files requiring updates:

| File | Changes |
|------|---------|
| `dev/scripts/sbs/utils.py:18` | Update `SBS_ROOT` or make dynamic |
| `dev/scripts/build.py:77` | Update `SBS_ROOT` |
| `dev/scripts/sbs/archive/chat_archive.py:138` | Update path normalization |
| `CLAUDE.md` | ~8 path references |
| `.claude/skills/update-and-archive/SKILL.md` | All repo paths |
| `.claude/skills/execute/SKILL.md` | Archive paths |
| `dev/scripts/VISUAL_COMPLIANCE.md` | Path examples |
| All `runway.json` files | Update `assetsDir` paths |

Path mapping:
- `./Dress` → `./toolchain/Dress`
- `./scripts/` → `./dev/scripts/`
- `./archive/` → `./storage/archive/`
- `./.refs/` → `./dev/.refs/`

### Phase 5: Final Commit & Push

**Agent 6: Commit and verify**
1. Stage all changes including .gitmodules
2. Commit with comprehensive message
3. Push monorepo to origin
4. Verify clean state
5. Test: clone fresh and run `git submodule update --init --recursive`

### Phase 6: Cleanup

1. Remove backup (after verification)
2. Remove temp migration directory
3. Run `/update-and-archive` to refresh all documentation

---

## Rollback Strategy

**Before submodule add (Phase 3):**
```bash
tar -xzvf backup-*.tar.gz  # Restore from backup
```

**After submodule add but before push:**
```bash
git submodule deinit -f .
rm -rf .git/modules/*
git reset --hard HEAD
# Restore repos from /tmp/sbs-migration/
```

---

## Validation

1. `git submodule status` shows 10 submodules
2. `git status` is clean
3. `python -m sbs --help` works from root
4. `python dev/scripts/build.py --dry-run` succeeds
5. Fresh clone + `git submodule update --init --recursive` works

---

## Agent Assignments

| Phase | Agent | Key Tasks |
|-------|-------|-----------|
| 0 | sbs-developer | Pre-flight checks, backup |
| 1 | sbs-developer | Create sbs-storage repo |
| 2 | sbs-developer | Directory structure, file moves |
| 3 | sbs-developer | Submodule conversion (critical) |
| 4 | sbs-developer | Path reference updates |
| 5 | sbs-developer | Commit, push, verify |
| 6 | Orchestrator | Cleanup, /update-and-archive |

Sequential execution. No parallel agents for this refactor.
