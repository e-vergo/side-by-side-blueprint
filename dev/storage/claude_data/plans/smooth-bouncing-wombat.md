# Plan: Machine Transfer Preparation

## Goal
Make the SBS monorepo portable so it can be cloned and set up on a new machine with minimal manual configuration. The transfer guide should enable future-Claude to achieve **development-ready state with first successful archive upload**.

## Background: Python Consolidation

**Problem found during audit:**
- `dev/scripts/.venv` uses Python 3.9.6 (violates `requires-python >= 3.10`)
- `forks/sbs-lsp-mcp/.venv` uses Python 3.14.2 (bleeding edge)
- Root `.venv` uses Python 3.10.19 (good)

**Solution:** Single root venv for sbs CLI. MCP server uses `uv run` (manages its own env).

## Changes Required

### Wave 1: Python Consolidation

1. Delete `dev/scripts/.venv` (obsolete, wrong Python version)
2. Ensure root `.venv` has sbs package installed
3. Update all documentation to use root venv

### Wave 2: Fix Hardcoded Paths

**File: `dev/scripts/sbs/core/utils.py`**
- Replace hardcoded `SBS_ROOT = Path("/Users/eric/GitHub/Side-By-Side-Blueprint")`
- New logic: Check `SBS_ROOT` env var first, then auto-detect from `__file__` location
- Auto-detect walks up from file to find directory containing `CLAUDE.md`

**File: `dev/scripts/sbs/archive/upload.py`**
- Line 57 has fallback hardcoded path
- Update to use the new `get_sbs_root()` function instead

### Wave 3: Update Transfer Guide

**File: `~/Library/Mobile Documents/com~apple~CloudDocs/SBS_archive/transfer_requirements.md`**

Complete rewrite with:
1. **Clear goal statement**: Development-ready + first successful archive upload
2. **Python setup**: Single root venv with uv
3. **Old repo cleanup section**: Delete old standalone clones after confirming monorepo works
4. **Success criteria checklist**: What "done" looks like for future-Claude

### Wave 4: Verification

1. Run `python3 -m sbs --help` to verify CLI still works
2. Run pytest on core tests
3. Run `sbs archive upload` to confirm full pipeline works

## Files Modified

| File | Change |
|------|--------|
| `dev/scripts/.venv/` | DELETE |
| `dev/scripts/sbs/core/utils.py` | SBS_ROOT auto-detection |
| `dev/scripts/sbs/archive/upload.py` | Remove hardcoded fallback |
| `~/...SBS_archive/transfer_requirements.md` | Complete rewrite |

## Gates

```yaml
gates:
  tests: all_pass
  regression: >= 0
```

## Verification Steps

1. `source .venv/bin/activate` (root venv)
2. `python3 -m sbs --help` - CLI loads
3. `pytest dev/scripts/sbs/tests/pytest/ -v --tb=short -x` - Tests pass
4. `python3 -m sbs archive upload --dry-run` - Archive pipeline works
