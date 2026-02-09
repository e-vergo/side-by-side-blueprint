# Implementation Plan: Issue Meta-Labels

**Issue:** #27 - Add meta-labels for issue categorization (SBS, Dev Tools, Misc)

---

## Summary

Add a second dimension of labeling to sort GitHub issues by domain area. This is orthogonal to existing type labels (bug/feature/idea).

---

## Scope

| Deliverable | Location |
|-------------|----------|
| GitHub labels | Repository settings (via `gh label create`) |
| MCP tool update | `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_tools.py` |
| Skill update | `.claude/skills/log/SKILL.md` |
| Retroactive labeling | All existing issues |

---

## Meta-Labels

| Label | Color | Scope |
|-------|-------|-------|
| `area:sbs` | `#0E8A16` (green) | Lean, Blueprint, Verso, Dress, Runway, graph, PDF, paper |
| `area:devtools` | `#5319E7` (purple) | Claude Code, MCP, self-improve, archive, skill, hook, tag |
| `area:misc` | `#FBCA04` (yellow) | Everything else |

---

## Implementation Waves

### Wave 1: Create GitHub Labels

```bash
gh label create "area:sbs" --color "0E8A16" --description "Core SBS toolchain: Lean, Blueprint, Verso" --repo e-vergo/Side-By-Side-Blueprint
gh label create "area:devtools" --color "5319E7" --description "Dev tools: MCP, archive, skills, Claude Code" --repo e-vergo/Side-By-Side-Blueprint
gh label create "area:misc" --color "FBCA04" --description "Miscellaneous" --repo e-vergo/Side-By-Side-Blueprint
```

**Validation:** `gh label list --repo e-vergo/Side-By-Side-Blueprint` shows all 3 labels

### Wave 2: Update MCP Tool

**File:** `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_tools.py`

Add `area` parameter to `sbs_issue_create`:
```python
def sbs_issue_create(
    ctx: Context,
    title: Annotated[str, Field(description="Issue title")],
    body: Annotated[Optional[str], Field(description="Issue body/description")] = None,
    label: Annotated[Optional[str], Field(description="Issue label: bug, feature, or idea")] = None,
    area: Annotated[Optional[str], Field(description="Area label: sbs, devtools, or misc")] = None,  # NEW
) -> IssueCreateResult:
```

Update label list construction:
```python
labels = ["ai-authored"]
if label:
    labels.append(label)
if area:
    labels.append(f"area:{area}")  # NEW
cmd.extend(["--label", ",".join(labels)])
```

**Validation:** Call `sbs_issue_create` with `area="devtools"` and verify label appears

### Wave 3: Update /log Skill

**File:** `.claude/skills/log/SKILL.md`

Add area inference keywords table:
```markdown
### Area Inference from Keywords

| Area | Keywords |
|------|----------|
| **sbs** | "lean", "verso", "blueprint", "dress", "runway", "graph", "pdf", "paper", "toolchain", "status", "color" |
| **devtools** | "mcp", "archive", "skill", "hook", "tag", "session", "claude", "self-improve", "oracle", "agent" |
| **misc** | (default if no keywords match) |
```

Add area parsing to workflow:
```markdown
6. **Infer area** from keywords if not explicit
7. **If area unclear:** Ask user with options:
   - [S] SBS - Core toolchain work
   - [D] DevTools - Development infrastructure
   - [M] Misc - Everything else
```

Add `--area` flag to invocation patterns:
```markdown
| `/log --area sbs <text>` | Explicit area, parse type from text |
```

**Validation:** Invoke `/log` with SBS-related text, verify area inference works

### Wave 4: Retroactive Labeling

Use `gh` CLI to label existing issues:

```bash
# Get all open issues
gh issue list --repo e-vergo/Side-By-Side-Blueprint --state all --json number,title,labels

# Apply labels based on title/content analysis
gh issue edit <number> --add-label "area:devtools" --repo e-vergo/Side-By-Side-Blueprint
```

**Assignment Strategy:**
- Issues #14-26 and #27-28: `area:devtools` (all self-improve/meta-tooling)
- Issue #4: `area:devtools` (self-improve skill)
- Future issues: Inferred by `/log` skill

**Validation:** `gh issue list` shows area labels on all issues

---

## Gates

```yaml
gates:
  tests: all_pass
  quality:
    T1: ">= 1.0"  # CLI execution (labels created)
    T2: ">= 0.8"  # Ledger population
```

---

## Validation Checklist

| # | Check | Method |
|---|-------|--------|
| V1 | 3 labels exist in GitHub | `gh label list` |
| V2 | MCP tool accepts `area` parameter | Test call via MCP |
| V3 | `/log` skill infers area from keywords | Manual test with SBS keywords |
| V4 | All existing issues have area labels | `gh issue list --json labels` |

---

## Critical Files

| File | Changes |
|------|---------|
| `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_tools.py` | Add `area` parameter (lines 1348-1429) |
| `.claude/skills/log/SKILL.md` | Add area inference section |

---

## Test Plan

1. **Wave 1 verification:**
   ```bash
   gh label list --repo e-vergo/Side-By-Side-Blueprint | grep "area:"
   # Expect: 3 lines (area:sbs, area:devtools, area:misc)
   ```

2. **Wave 2 verification:**
   - Create test issue with area parameter
   - Verify label appears on GitHub

3. **Wave 3 verification:**
   - Invoke `/log lean graph layout bug`
   - Expect: area:sbs inferred

4. **Wave 4 verification:**
   ```bash
   gh issue list --state all --json number,labels | jq '.[] | select(.labels | map(.name) | any(startswith("area:")))'
   # Expect: All issues have area labels
   ```
