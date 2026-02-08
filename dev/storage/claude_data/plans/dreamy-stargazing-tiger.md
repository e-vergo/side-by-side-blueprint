# Task Crush: 10 Issues in 6 Waves

**Issues:** #148, #160, #161, #162, #163, #164, #166, #167, #149, #99
**Branch:** `task/crush-10-issues`

## Wave Summary

| Wave | Issues | Agents | Type |
|------|--------|--------|------|
| 0 | #148 (close), #160 (tag scope) | orchestrator + 1 | Investigation + fix |
| 1 | #161, #162 | 1 | Docs to sbs-developer.md |
| 2 | #163, #149 | 2 parallel | MCP venv + loop doc |
| 3 | #166 | 1 | Absorb self-improve into introspect |
| 4 | #164, #167 | 2 parallel | Post-restructure cleanup |
| 5 | #99 | 1-2 sequential | Taxonomy unification (6 phases) |

**Dependencies:** Wave 4 depends on Wave 3. Wave 5 depends on Wave 0.

## Gates

```yaml
gates:
  tests: all_pass
  test_tier: evergreen
  regression: >= 0
```

---

## Wave 0: #148 (close) + #160 (tag scope fix)

### #148 — Close with explanation (orchestrator)
Tactic toggle is fully implemented (SubVerso, Verso, CSS, JS). SBS-Test proofs are single-tactic — content gap, not a bug. Close via `sbs_issue_close`.

### #160 — Add scope field to auto-tags (1 agent)

**Root cause:** `build_tagging_context()` extracts session-constant fields from `claude_data` (token counts, tool counts, model versions). Hooks in `session_profiler.py` produce `session:*`, `token:*`, `thinking:*`, `model:*` tags uniformly for all entries.

**Fix — namespace split (Option 2):**

1. Add `scope: entry | session | both` to each tag in `agent_state_taxonomy.yaml`
2. Add `scope` to each rule in `rules.yaml`
3. Split `build_tagging_context()` into `build_entry_context()` + `build_session_context()`
4. Rule evaluation uses appropriate context based on rule's `scope`
5. Hooks declare scope via module-level `SCOPE` constant
6. Update tests to validate scope field exists and entries vary within sessions

**Files:**
- `dev/storage/tagging/agent_state_taxonomy.yaml` — add scope field
- `dev/storage/tagging/rules.yaml` — add scope to rules
- `dev/scripts/sbs/archive/tagger.py` — split context, scope-aware eval
- `dev/storage/tagging/hooks/session_profiler.py` — declare session scope
- `dev/storage/tagging/hooks/outcome_tagger.py` — split session/entry
- `dev/storage/tagging/hooks/signal_detector.py` — review scope
- `dev/scripts/sbs/tests/pytest/test_agent_state_taxonomy.py` — scope validation
- `dev/scripts/sbs/tests/pytest/test_tagger_v2.py` — entry variance test

---

## Wave 1: #161 + #162 (docs additions)

**1 agent — both touch `.claude/agents/sbs-developer.md`**

Add two new sections:

**"CLI Gotchas"** — `gh` CLI infers wrong repo in showcase dirs. Always use `--repo e-vergo/Side-By-Side-Blueprint`.

**"Testing Standards"** — Tests must import/call actual functions. Simulation tests (reimplementing logic inline) are prohibited. Integration > unit for MCP tools.

---

## Wave 2: #163 + #149 (parallel)

### #163 — sbs_run_tests MCP venv support (Agent A)

Add `repo: Optional[str]` parameter to `sbs_run_tests` in `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_tools.py:482`.

- Map `repo="mcp"` to `forks/sbs-lsp-mcp/.venv/bin/pytest` + `tests/` dir
- Unknown repo → error
- `repo=None` → existing behavior
- Add fallback note to sbs-developer.md Testing Standards

### #149 — Loop opportunities document (Agent B)

Create `dev/markdowns/permanent/LOOP_OPPORTUNITIES.md` cataloging 5 layers:
1. Dev tool ↔ dev tool (archive → oracle → introspect pipeline)
2. Dev tool ↔ Claude Code native (MCP + Task agents + TodoWrite)
3. Dev tool ↔ application (Lean LSP on Lean code)
4. Claude Code native ↔ application (Bash/Edit on app files)
5. Compound loops (issue → task → build → QA → issue)

Framework-general where possible, SBS-specific where concrete.

---

## Wave 3: #166 (absorb self-improve into introspect)

**1 agent — largest single change**

Merge self-improve (740 lines, 5 phases) into introspect (277 lines, 3 phases).

**Merged invocation:**
- `/introspect 2` → L2 cycle: discovery, selection, dialogue, logging, archive (all from self-improve)
- `/introspect 3+` → L(N) meta-analysis: ingestion, synthesis, archive (existing introspect)
- L1 stays with /update-and-archive

**Files:**
- `.claude/skills/introspect/SKILL.md` — major rewrite (merge both skills, version 2.0.0)
- `.claude/skills/self-improve/` — delete directory
- `CLAUDE.md` — remove /self-improve entry, update /introspect description, update multiagent refs (lines ~26, 31, 148, 493: "self-improve" → "introspect")
- `.claude/agents/sbs-developer.md` — update multiagent ref (line ~146)
- `.claude/skills/update-and-archive/SKILL.md` — update L1 consumer ref to "/introspect 2"
- `.claude/skills/log/SKILL.md` — update area label ref

**Verification:** `grep -r "self-improve" .claude/` returns zero hits in skill/agent files (taxonomy labels excepted).

---

## Wave 4: #164 + #167 (parallel, post-Wave 3)

### #164 — Verification sampling protocol (Agent A)

Add "Verification Sampling" substep to L2 Discovery phase in merged `introspect/SKILL.md`:
- Each L2 cycle selects 2-3 prior guidance additions
- Search session JSONL/archive for adoption evidence
- Record status: ADOPTED / NOT YET OBSERVED / INEFFECTIVE
- Escalation after 2 cycles without evidence
- Add "## Verification" section to L2 summary output template

### #167 — Audit skills for self-directed patterns (Agent B)

Audit all SKILL.md files for embedded source-of-truth data that agents should read from source:
- `qa/SKILL.md` — already self-directed (reads criteria.py). Confirm no changes.
- `task/SKILL.md` — check for embedded gate thresholds, test catalogs
- `introspect/SKILL.md` — check if Finding-to-Label Mapping duplicates taxonomy
- `log/SKILL.md` — check for embedded label lists
- `update-and-archive/SKILL.md` — check for embedded file lists

Replace any embedded data with read-from-source instructions.

---

## Wave 5: #99 (taxonomy unification — 6 phases)

### Phase 1: Design unified YAML schema
Create `dev/storage/taxonomy.yaml` (v3.0):
```yaml
dimensions:
  origin:
    description: "..."
    color: "#9E9E9E"           # for GH sync (issue-context only)
    entries:
      - name: "origin:user"
        description: "..."
        contexts: [issues]      # issues | archive | both
        color: "#9E9E9E"        # optional override
      - name: "phase:alignment"
        description: "..."
        contexts: [archive]
        scope: entry            # from Wave 0 (#160)
```

### Phase 2: Migrate both taxonomies
Combine 107 labels + 138 tags. Annotate every entry with `contexts`. Resolve `scope:*` dimension overlap (same semantics — merge). Keep old files as `.bak` until consumers updated.

### Phase 3: Update validation/loading layer
Refactor `dev/scripts/sbs/labels/__init__.py`:
- `load_taxonomy()` → new unified schema
- `get_all_labels(context=None)` → context filtering
- `get_all_labels(context="issues")` → issue-scoped only
- All existing functions preserved with backward-compatible signatures

### Phase 4: Update GH label sync
`dev/scripts/sbs/labels/sync.py` — filter to `contexts: [issues, both]` before syncing.

### Phase 5: Update auto-tagger
`dev/scripts/sbs/archive/tagger.py` — load from unified file, filter to `contexts: [archive, both]`. Update `rules.yaml` references.

### Phase 6: Update tests + cleanup
- Merge `test_taxonomy.py` + `test_agent_state_taxonomy.py` → unified test
- Test context filtering, scope field, no naming collisions
- Delete old taxonomy files and `.bak` copies
- Update all path references (CLAUDE.md, log/SKILL.md, etc.)

**Files:**
- `dev/storage/taxonomy.yaml` (new)
- `dev/storage/labels/taxonomy.yaml` (delete)
- `dev/storage/tagging/agent_state_taxonomy.yaml` (delete)
- `dev/scripts/sbs/labels/__init__.py` (refactor)
- `dev/scripts/sbs/labels/sync.py` (filter by context)
- `dev/scripts/sbs/archive/tagger.py` (unified loader)
- `dev/storage/tagging/rules.yaml` (update refs)
- `dev/scripts/sbs/tests/pytest/test_taxonomy.py` (unified tests)
- `dev/scripts/sbs/tests/pytest/test_agent_state_taxonomy.py` (merge/delete)

---

## File Collision Matrix

No file is written by two agents within the same wave:

| File | W0 | W1 | W2 | W3 | W4 | W5 |
|------|----|----|----|----|----|----|
| `agent_state_taxonomy.yaml` | W | | | | | D |
| `tagger.py` | W | | | | | W |
| `rules.yaml` | W | | | | | W |
| `hooks/*.py` | W | | | | | |
| `sbs-developer.md` | | W | W | W | | |
| `sbs_tools.py` | | | W | | | |
| `introspect/SKILL.md` | | | | W | W | |
| `self-improve/` | | | | D | | |
| `CLAUDE.md` | | | | W | | W? |
| `labels/__init__.py` | | | | | | W |
| `taxonomy.yaml` (new) | | | | | | C |

W=Write, C=Create, D=Delete

## Verification

After all waves:
1. `pytest dev/scripts/sbs/tests/pytest -m evergreen --tb=short` — all pass
2. `grep -r "self-improve" .claude/skills/ .claude/agents/` — zero hits (except taxonomy)
3. `python3 -c "from sbs.labels import get_all_labels; print(len(get_all_labels(context='issues')))"` — returns issue-scoped count
4. `sbs_run_tests(repo="mcp")` — MCP tests run successfully
5. Unified taxonomy loads without error
