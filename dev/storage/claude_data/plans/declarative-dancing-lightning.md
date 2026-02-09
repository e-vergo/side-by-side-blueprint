# SBS/SLS Separation Plan (Issue #266)

## Context

The monorepo at `e-vergo/Side-By-Side-Blueprint` entangles two distinct concerns: the SBS formalization toolchain (Lean proofs + LaTeX) and the SLS orchestration framework (archive, skills, introspection). This plan separates them into independent repos so SBS can ship as a clean tool for the Lean community and SLS can evolve as a general-purpose orchestration framework.

## Target Repos

| Repo | GitHub | Contents |
|------|--------|----------|
| **SBS** | `e-vergo/Side-By-Side-Blueprint` (existing) | Toolchain + showcase + Lean forks + `sbs` CLI + build scripts |
| **SLS** | `e-vergo/SLS-Strange-Loop-Station` (new) | Archive + skills + agents + `sls` CLI + `sls-mcp` |
| **lean-lsp-mcp** | `e-vergo/lean-lsp-mcp` (new) | 18 Lean LSP tools (standalone, domain-agnostic) |
| **sbs-core** | Local pip package | Shared Python: `git_ops`, `branch_ops`, `utils`, `timing`, `ledger` |

## Key Design Decisions

1. **Existing repo stays SBS** — preserves submodule URLs, git history, GitHub stars
2. **Archive imports already guarded** — `orchestrator.py:72-83` uses `try/except` for `sbs.archive`; no-ops when absent
3. **MCP tools cleanly separated** — Lean tools are `@mcp.tool()` inline in `server.py`; SBS/SLS tools use `register_*_tools()` modules
4. **`SBS_ROOT` already env-var-driven** — `utils.py:27-29` checks `SBS_ROOT` env var first

## Execution Waves

### Wave 0: Prerequisites (sequential, 2 agents)

| Agent | Action |
|-------|--------|
| A1 | `gh repo create e-vergo/lean-lsp-mcp --public` and `gh repo create e-vergo/SLS-Strange-Loop-Station --public`. Clone both to `/Users/eric/GitHub/`. |
| A2 | Create `sbs-core` package at `/Users/eric/GitHub/sbs-core/` from `dev/scripts/sbs/core/` (5 files). `pyproject.toml` with namespace `sbs_core`. Both repos will `pip install -e ../sbs-core`. |

**Gate:** Both repos exist. `sbs-core` installs via pip.

### Wave 1: lean-lsp-mcp + SLS population + SBS cleanup (4 parallel agents)

These 3 workstreams are independent — all modify non-overlapping files.

| Agent | Target | Action |
|-------|--------|--------|
| A1 | `lean-lsp-mcp/` repo | Extract 18 `lean_*` tool defs from `sbs-lsp-mcp/server.py` + supporting modules (`client_utils.py`, `outline_utils.py`, `profile_utils.py`, `search_utils.py`, `loogle.py`, `file_utils.py`, `utils.py`, `models.py`). New `server.py` + `pyproject.toml`. |
| A2 | `SLS/` repo | Copy: `dev/scripts/sbs/archive/`, `labels/`, `readme/`, `test_catalog/`, `commands/` -> `dev/scripts/sls/`. Rename imports `sbs.*` -> `sls.*`. Create `sls` CLI from SLS commands in `cli.py`. Create `pyproject.toml`. Set up `.gitmodules` (storage, vscode-lean4). |
| A3 | `SLS/.claude/` + `SLS/CLAUDE.md` + `SLS/dev/markdowns/` | Copy agent definitions. Extract SLS sections from CLAUDE.md (orchestration, skills, archive, agent patterns, user prefs). Copy `dev/markdowns/`. |
| A4 | SBS repo cleanup | Remove SLS commands from `sbs/cli.py`. Remove `dev/scripts/sbs/archive/`, `labels/`, `readme/`, `test_catalog/`, `commands/watch.py`, `commands/dev.py`. Remove SLS tests. Update `pyproject.toml` to dep on `sbs-core`. |

**Gate:** `python -m sls --help` works in SLS. `python -m sbs --help` works in SBS (no archive commands). No broken imports.

### Wave 2: MCP server split (4 parallel agents)

| Agent | Target | Action |
|-------|--------|--------|
| A1 | `sbs-lsp-mcp/server.py` | Remove 18 `lean_*` tool definitions. Rename package to `sls-mcp`. Keep `register_sbs_tools`, `register_skill_tools`, browser, zulip. |
| A2 | `SLS/forks/sls-mcp/` tool renaming | Rename files: `sbs_tools.py` -> `sls_tools.py`, `sbs_models.py` -> `sls_models.py`. Rename 55 SLS tool functions: `sbs_archive_state` -> `sls_archive_state`, `sbs_skill_*` -> `sls_skill_*`, etc. |
| A3 | SBS repo: create `sbs-mcp/` | Extract Category B tools (8): `sbs_build_project`, `sbs_validate_project`, `sbs_serve_project`, `sbs_inspect_project`, `sbs_run_tests`, `sbs_last_screenshot`, `sbs_visual_history`, `ask_oracle` (concept index only). New `server.py` + `pyproject.toml`. |
| A4 | Both repos: `.mcp.json` | SBS: `lean-lsp` + `sbs-mcp` servers. SLS: `lean-lsp` + `sls-mcp` servers. Remove old `sbs-lsp` entry from both. |

**Gate:** All MCP servers start. `lean_goal`, `sbs_build_project`, `sls_archive_state` all respond from their respective servers.

### Wave 3: Documentation + references + CLAUDE.md (3 parallel agents)

| Agent | Target | Action |
|-------|--------|--------|
| A1 | SBS `CLAUDE.md` | Rewrite to SBS-only: build conventions, dependency chain, quality validators, Lean patterns, 6-status color model. Remove orchestration, skills, archive, agent patterns. Target ~300 lines. |
| A2 | `SLS/.claude/agents/*.md` + `SLS/CLAUDE.md` | Update all MCP tool references: `mcp__sbs-lsp__sbs_*` -> `mcp__sls-mcp__sls_*`. Update `mcp__sbs-lsp__lean_*` -> `mcp__lean-lsp__lean_*`. |
| A3 | SBS `.gitmodules` + cleanup | Remove `dev/storage`, `forks/vscode-lean4`, `forks/sbs-lsp-mcp` from `.gitmodules`. Remove those directories. Remove `.claude/agents/` (agents live in SLS). |

**Gate:** No stale tool references in either repo. `.gitmodules` consistent in both.

### Wave 4: Tests + verification (2 parallel agents)

| Agent | Target | Action |
|-------|--------|--------|
| A1 | SBS repo | Run `python build.py --dry-run` in SBS-Test. Run SBS pytest suite. Verify no `sbs.archive` imports. Verify MCP config. |
| A2 | SLS repo | Copy SLS tests (`test_archive_invariants.py`, `test_gates.py`, `test_self_improve.py`, `test_tagger_v2.py`, `test_taxonomy.py`, `test_ledger_health.py`). Update imports. Run SLS pytest suite. Verify `sls-mcp` starts. |

**Gate:** All tests pass in both repos. No cross-repo import leaks.

## Risk Mitigation

- **Highest risk:** Tool renaming (Wave 2-3). 55 tools across ~350K lines. Mitigation: systematic grep-based verification after each rename batch.
- **Medium risk:** Import path changes (`sbs.*` -> `sls.*`). Mitigation: agents run `python -c "import sls"` after each module move.
- **Low risk:** lean-lsp extraction (clean boundary, no SBS/SLS deps).

## Open Questions (Resolved)

| Question | Decision |
|----------|----------|
| Shared infrastructure | `sbs-core` pip package |
| CLI namespace | `sbs` (build) + `sls` (orchestration) |
| Oracle placement | `ask_oracle` in sbs-mcp (concept index only); archive queries in sls-mcp |
| Validators | Stay in SLS (orchestration-driven), query SBS artifacts |
| VSCode fork | Stays in SLS |
| Storage | Stays in SLS as submodule |
| New SBS repo approach | Fresh repo (existing repo IS the SBS repo; SLS is new) |

## Verification

1. SBS: `cd toolchain/SBS-Test && python ../../dev/scripts/build.py --dry-run`
2. SBS: `pytest dev/scripts/sbs/tests/pytest/ -m evergreen --tb=short`
3. SLS: `python -m sls archive --help`
4. SLS: `pytest dev/scripts/sls/tests/ --tb=short`
5. MCP: Start each server, verify tool registration counts (18 lean, 8 sbs, 55 sls)
6. Grep: Zero matches for `from sbs.archive` in SBS repo, zero matches for `mcp__sbs-lsp__` in either repo
