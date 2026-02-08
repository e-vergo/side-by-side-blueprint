# Plan: `/introspect` Skill + First L3 Execution (#159)

## Summary

Create a new `/introspect` skill that produces L(N) meta-analysis documents by reading all L(N-1) documents. Then execute the first L3 cycle (reading 5 L2 summaries).

## Wave Structure

### Wave 0: Infrastructure (1 agent)

| File | Action |
|------|--------|
| `dev/storage/archive/meta-summaries/.gitkeep` | Create directory + marker |

### Wave 1: Skill Definition + Registration (2 parallel agents)

**Agent A** — Skill definition:

| File | Action |
|------|--------|
| `.claude/skills/introspect/SKILL.md` | Create new skill (details below) |

**Agent B** — Registration updates:

| File | Action |
|------|--------|
| `CLAUDE.md` | Add `/introspect` to Custom Skills section |
| `.claude/skills/self-improve/SKILL.md` | Update Introspection Hierarchy table (L3 row) |

### Wave 2: First L3 Document (1 agent)

| File | Action |
|------|--------|
| `dev/storage/archive/meta-summaries/L3-<entry-id>.md` | Write first L3 meta-analysis |

Reads all 5 L2 summaries, synthesizes across 6 analysis dimensions (see below).

---

## Skill Design: `/introspect`

**Phases:** `ingestion` -> `synthesis` -> `archive`

**Invocation:** `/introspect <N>` where N >= 3 (required argument)

**Input/Output mapping:**

| Level | Input | Output |
|-------|-------|--------|
| 3 | `dev/storage/archive/summaries/*.md` | `dev/storage/archive/meta-summaries/L3-<id>.md` |
| 4+ | `dev/storage/archive/meta-summaries/L<N-1>-*.md` | `dev/storage/archive/meta-summaries/L<N>-<id>.md` |

**Minimum viable input:** 2+ L(N-1) documents required. Fewer = skill fails gracefully.

**Archive protocol:** Stateful — uses `sbs_skill_start/transition/end` MCP calls.

**Agent concurrency:** None. Sequential read-synthesize-write.

**L3 Analysis Dimensions:**
1. Skill Evolution Trajectory
2. Recurring Friction Inventory (problems in 3+ L2 docs despite "fixes")
3. Metric Trajectory Analysis (task completion, tag signal, quality coverage trends)
4. Intervention Effectiveness (resolution rate by intervention type)
5. Observation Layer Meta-Assessment
6. Data Speaks (raw aggregated tables, no commentary)
7. Recommendations for Next L3 Cycle

---

## Registration Updates

**CLAUDE.md** (Custom Skills section, after `/update-and-archive`):

```markdown
### `/introspect`

Meta-improvement analysis across introspection hierarchy levels. Reads all L(N-1) documents to produce an L(N) meta-summary.

**Usage:** `/introspect 3` (reads L2 summaries, produces L3 meta-analysis)

**Workflow:** Ingestion -> Synthesis -> Archive

**Location:** `.claude/skills/introspect/SKILL.md`
```

**Self-improve SKILL.md** — Replace L(N) placeholder row with concrete L3 + generic L(N) rows.

---

## Gates

```yaml
gates:
  tests: all_pass
  test_tier: evergreen
  regression: >= 0
```

No visual validators — task produces only markdown and skill definitions.

## Verification

1. Evergreen tests pass
2. `.claude/skills/introspect/SKILL.md` exists with correct frontmatter
3. `dev/storage/archive/meta-summaries/L3-*.md` exists and is non-empty
4. CLAUDE.md contains `/introspect` entry
5. Self-improve SKILL.md Introspection Hierarchy table has L3 row
