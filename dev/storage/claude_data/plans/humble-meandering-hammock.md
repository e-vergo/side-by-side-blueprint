# L4 Meta-Introspection Execution Plan

**Task:** Execute all 9 child issues of #241 in 3 waves
**Issues:** #232, #233, #234, #235, #236, #237, #238, #239, #240
**Scope:** Single `/task` invocation, 3 sequential waves of up to 4 concurrent `sbs-developer` agents

---

## Wave 0: Investigation + Quick Wins + Critical Path

**4 concurrent agents. No file overlap.**

### Agent 0A: #238 — Investigate Finalization Failures + Concrete Fixes

**Problem:** Finalization is the most common failure substate across 4/5 L2 cycles but never investigated.

**Deliverables:**
1. Examine archive entries with `state_transition="phase_fail"` or incomplete task sessions
2. Identify common failure patterns (context compaction, ceremony friction, state staleness)
3. **Produce concrete fixes** in `skill_tools.py` finalization phase where possible
4. Write findings as comment on #238

**Files (write):** `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/skill_tools.py` (lines 708-817, finalization phase)
**Files (read-only):** Archive entries, `duckdb_layer.py`, session JSONL files

### Agent 0B: #240 — Reference USER_PROFILE.md in CLAUDE.md

**Deliverable:** Add one row to CLAUDE.md Reference Documents table.

**Files (write):** `CLAUDE.md` (Reference Documents table only)

### Agent 0C: #233 — Reduce Header Taxonomy from 10 to ~6

**Problem:** 86.9% of AskUserQuestion headers are ad-hoc; the 10-header taxonomy doesn't match reality.

**Deliverables:**
1. Query `sbs_question_stats()` to identify actually-used headers
2. Replace 10-header taxonomy in CLAUDE.md with ~6 effective ones

**Files (write):** `CLAUDE.md` (Standard Header Taxonomy section only — different section from 0B)

### Agent 0D: #237 — Fix Tag Signal Pipeline via DuckDB Entry-Level Extraction

**Problem:** Tags at 0.0 signal across 5 L2 cycles. Root cause: `build_tagging_context()` in `tagger.py:322-423` has session-constant fields that apply identical tags to every entry.

**Deliverables:**
1. Modify `tagger.py` context builders to eliminate session-constant noise
2. Update `rules.yaml` to use entry-level discriminants (phase transitions, build outcomes, quality deltas)
3. Verify via `sbs_tag_effectiveness` that signal improves from 0.0

**Files (write):**
- `dev/scripts/sbs/archive/tagger.py` (lines 322-423)
- `dev/storage/tagging/rules.yaml`

---

## Wave 1: Core Pipeline Fixes

**4 concurrent agents. Depends on Wave 0 completion.**

### Agent 1A: #232 — Merge Improvement Captures into L2 Discovery

**Problem:** 21 improvement captures invisible to `sbs_entries_since_self_improve`.

**Deliverables:**
1. Modify `duckdb_layer.py:817-880` to include improvement-trigger entries
2. OR add dedicated `sbs_improvement_review()` tool

**Files (write):**
- `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/duckdb_layer.py` (entries_since_self_improve)
- `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_tools.py` (if new tool)
- `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_models.py` (if new model)

### Agent 1B: #235 — Instrument Oracle-First Compliance + MCP Tool Call Tracking

**Problem:** Oracle-first mandate has zero tracking. MCP tool call data not captured in archive.

**Expanded scope:** Track MCP tool calls in archive entries for mining.

**Deliverables:**
1. Modify `extractor.py` to extract per-tool-call data from `~/.claude` session JSONL (tool name, timestamp, duration)
2. Add `mcp_tool_calls` field to claude_data sidecar
3. Add tagging rule detecting oracle-answerable patterns without preceding `ask_oracle`
4. Surface in `sbs_tag_effectiveness` output

**Files (write):**
- `dev/scripts/sbs/archive/extractor.py`
- `dev/scripts/sbs/archive/entry.py` (if adding field)
- `dev/storage/tagging/rules.yaml` (new rule — appends to 0D's changes)
- `dev/scripts/sbs/archive/tagger.py` (new context fields — appends to 0D's changes)

### Agent 1C: #236 — Add Visual Verification Gate to Task Finalization

**Problem:** 397 visual-change entries, only 7 QA sessions. No gate enforces verification.

**Depends on:** #237 (Wave 0D) for reliable tag signal.

**Deliverables:**
1. Add soft gate in `skill_tools.py` finalization (lines 708-817)
2. Warn if visual-change/css-modified tags present but no screenshot evidence
3. Soft gate: `requires_approval=True` with explanation, doesn't block

**Files (write):**
- `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/skill_tools.py` (finalization, lines 708-817)
- `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/gate_validation.py` (new gate type)

### Agent 1D: #234 — Adaptive Retrospective Templates

**Problem:** Clean sessions produce vacuous 5-section retrospectives.

**Depends on:** #238 (Wave 0A) findings on what "clean session" means.

**Deliverables:**
1. Modify `skill_tools.py:2371-2434` retrospective phase
2. Detect friction metrics (corrections, backward transitions, retries)
3. Select compressed (1-2 sections) vs full (5 sections) template

**Files (write):** `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/skill_tools.py` (retrospective, lines 2371-2434)

---

## Wave 2: Capstone

**1 agent. Depends on Wave 1 (#232) completion.**

### Agent 2A: #239 — Replace Closure Rate with Verification Rate

**Problem:** Goodhart's Law — 100% closure, 0% verification.

**Deliverables:**
1. Define verification rate: issues with confirmed fix (code+test or guidance+adoption)
2. Add verification tracking in `duckdb_layer.py`
3. Modify L2 introspection reporting (`skill_tools.py:1335-1586`) to surface verification rate
4. Add `sbs_verification_rate()` analysis tool if warranted

**Files (write):**
- `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/duckdb_layer.py`
- `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/skill_tools.py` (L2 introspection)
- `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_tools.py` (new tool)
- `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_models.py` (new model)

---

## Collision Avoidance

| File | W0A | W0B | W0C | W0D | W1A | W1B | W1C | W1D | W2A |
|------|-----|-----|-----|-----|-----|-----|-----|-----|-----|
| `CLAUDE.md` | | ref docs | headers | | | | | | |
| `tagger.py` | | | | context builders | | new fields | | | |
| `rules.yaml` | | | | rule conditions | | new rule | | | |
| `skill_tools.py` | finalization | | | | | | finalization | retrospective | introspect |
| `duckdb_layer.py` | | | | | entries_since | | | | verification |
| `gate_validation.py` | | | | | | | gate type | | |
| `extractor.py` | | | | | | tool extraction | | | |

- W0B/W0C: both CLAUDE.md, different sections — safe parallel
- W0D->W1B: tagger.py/rules.yaml sequential — W1B appends to W0D's work
- W0A->W1C: skill_tools.py finalization sequential — W1C adds gate to W0A's fixes
- W1C/W1D: skill_tools.py parallel — different functions (finalization vs retrospective)

---

## Gates (between waves)

- **Evergreen tests:** `pytest sbs/tests/pytest -m evergreen` — 100% pass
- **MCP tests:** `sbs_run_tests(repo="mcp")` — validate sbs-lsp-mcp changes
- **Tag signal (after W0):** `sbs_tag_effectiveness` shows improvement from 0.0

---

## Verification

After all waves:
1. `sbs_run_tests()` — all tests pass
2. `sbs_run_tests(repo="mcp")` — MCP tests pass
3. `sbs_tag_effectiveness()` — signal > 0.0
4. `sbs_entries_since_self_improve()` — returns improvement captures
5. Manual: trigger a clean session retrospective and verify compressed template
6. Close all 9 child issues + parent #241
