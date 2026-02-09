# Plan: SLS Repo Restructuring — MCP Relocation + Path Fix + Cleanup

## Context

The user restructured SLS to cleanly separate SLS (orchestration) from SBS (Lean toolchain). SLS now contains only: `.claude/`, `SBS/` (submodule), `dev/`, config files. All duplicate SBS submodules (toolchain/, showcase/, forks/Lean*) were removed from the SLS root.

Remaining work:
1. MCP servers lost their home (was `forks/sls-mcp/`, deleted)
2. `.gitmodules` has stale entries for removed submodules
3. Git index has stale gitlinks for removed submodules
4. SBS nested submodules are empty (need init)
5. `SBS_ROOT` / `ARCHIVE_DIR` path resolution is broken
6. `.mcp.json` points to nonexistent path

## Changes

### 1. Restore MCP servers to `dev/mcp/`

Recover `sls-mcp` from git and place at `dev/mcp/sls-mcp/`:
```bash
git checkout HEAD -- forks/sls-mcp
mkdir -p dev/mcp
mv forks/sls-mcp dev/mcp/sls-mcp
```

Check if `sbs-mcp` exists in git history and restore to `dev/mcp/sbs-mcp/` if so.

### 2. Clean SLS `.gitmodules`

Keep only:
- `SBS`
- `dev/storage`

Remove ALL other entries (LeanArchitect, subverso, verso, Dress, Runway, SBS-Test, dress-blueprint-action, GCR, PNT, vscode-lean4). These all live in SBS.

### 3. Remove stale gitlinks from index

```bash
git rm --cached forks/LeanArchitect forks/subverso forks/verso
git rm --cached toolchain/Dress toolchain/Runway toolchain/SBS-Test toolchain/dress-blueprint-action
git rm --cached showcase/General_Crystallographic_Restriction showcase/PrimeNumberTheoremAnd showcase/ReductiveGroups
```

Also remove the `forks/sls-mcp` tracking (since it moved to `dev/mcp/sls-mcp`).

### 4. Initialize SBS nested submodules

```bash
cd SBS && git submodule update --init --recursive
```

This populates Dress, Runway, SBS-Test, LeanArchitect, etc. inside the SBS submodule.

### 5. Add `SLS_ROOT` + fix path resolution

**`dev/mcp/sls-mcp/src/sls_mcp/sls_utils.py`:**
- Rename `_find_sbs_root()` → `_find_sls_root()`
- Export `SLS_ROOT` (from `SLS_ROOT` env var or walk-up)
- Derive `SBS_ROOT = SLS_ROOT / "SBS"` (or from env var)
- Compute `ARCHIVE_DIR = SLS_ROOT / "dev" / "storage"` locally

**`dev/mcp/sls-mcp/src/sls_mcp/*.py`** — All `SBS_ROOT / "dev" / ...` → `SLS_ROOT / "dev" / ...`:
- `browser_tools.py:39`, `gate_validation.py:35-37`
- `skill_tools.py:67,199,551,660,664,671,1768,2457,3001`
- `server.py:187`, `sls_tools.py:490-491,518,627,1568,3633`

Keep `SBS_ROOT` for Lean project paths (now `SLS_ROOT / "SBS" / "toolchain/..."` etc.).

### 6. Update `.mcp.json`

```json
{
  "mcpServers": {
    "lean-lsp": {
      "command": "uv",
      "args": ["run", "--directory", "/Users/eric/GitHub/lean-lsp-mcp", "lean-lsp-mcp"]
    },
    "sls-mcp": {
      "command": "uv",
      "args": ["run", "--directory", "/Users/eric/GitHub/SLS-Strange-Loop-Station/dev/mcp/sls-mcp", "sls-mcp"],
      "env": {
        "SBS_ROOT": "/Users/eric/GitHub/SLS-Strange-Loop-Station/SBS",
        "SLS_ROOT": "/Users/eric/GitHub/SLS-Strange-Loop-Station",
        "ZULIP_ENABLED": "1"
      }
    },
    "vscode": { ... },
    "vscode-mcp": { ... }
  }
}
```

### 7. Update `CLAUDE.md` — Repo structure + path docs

- Update repo topology diagram (remove `forks/`, `toolchain/`, `showcase/` from SLS level)
- Update MCP server paths (`forks/sls-mcp/` → `dev/mcp/sls-mcp/`)
- Document `SLS_ROOT` + `SBS_ROOT` env vars
- Update `SBS_ROOT` resolution paragraph

### 8. Clean SBS `.gitmodules`

Remove stale SLS entries: `dev/storage`, `SBS` (self-reference). Keep `forks/vscode-lean4` (SBS-specific). Commit inside SBS submodule.

---

## Verification

1. `ls dev/mcp/sls-mcp/src/sls_mcp/server.py` — MCP server code in place
2. `cat .gitmodules` — only SBS, dev/storage, (optionally vscode-lean4)
3. `git submodule status` — no stale/orphaned entries
4. `ls SBS/toolchain/Dress/lakefile.lean` — SBS nested submodules populated
5. `ARCHIVE_DIR` resolves to `SLS/dev/storage` (with archive contents)
6. `.mcp.json` points to correct paths
