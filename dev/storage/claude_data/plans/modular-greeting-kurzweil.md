# PR-Based Workflow Integration Plan

## Summary

Move from direct-to-main commits to a PR-based workflow where:
1. All changes go through feature branches
2. PRs are created when execution plans are approved
3. PRs are auto-merged when gates pass
4. Full AI attribution on all PRs

---

## Design Decisions (from Alignment)

| Aspect | Decision |
|--------|----------|
| Merge authority | Auto-merge if gates pass |
| Branch naming | `task/<issue-or-id>-<slug>` (human-readable) |
| Main repo | PRs required |
| toolchain/* | PRs required |
| showcase/* | PRs required |
| forks/* | Direct commits (tracking upstream) |
| dev/storage | Direct commits (data only) |
| PR lifecycle | Created at plan approval, merged when gates pass |
| PR body | Summary + link to plan file |
| Multi-repo changes | Submodule commits direct, main repo PR captures bump |
| AI attribution | `ai-authored` label + footer |

---

## Implementation Waves

### Wave 1: MCP PR Tools (sbs-lsp-mcp)

**Files to modify:**
- [sbs_models.py](forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_models.py) - Add PR models
- [sbs_tools.py](forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_tools.py) - Add 4 PR tools

**New models:**
```python
class GitHubPullRequest(BaseModel):
    number: int
    title: str
    state: str              # "open", "closed", "merged"
    labels: List[str]
    url: str
    body: Optional[str]
    base_branch: str
    head_branch: str
    draft: bool
    mergeable: Optional[bool]
    created_at: Optional[str]

class PRCreateResult(BaseModel):
    success: bool
    number: Optional[int]
    url: Optional[str]
    error: Optional[str]

class PRMergeResult(BaseModel):
    success: bool
    sha: Optional[str]      # Merge commit SHA
    error: Optional[str]
```

**New tools:**

| Tool | gh Command | Purpose |
|------|------------|---------|
| `sbs_pr_create` | `gh pr create` | Create PR from current branch |
| `sbs_pr_list` | `gh pr list` | List open PRs |
| `sbs_pr_get` | `gh pr view` | Get PR details |
| `sbs_pr_merge` | `gh pr merge` | Merge PR (squash default) |

**Implementation pattern (matches existing issue tools):**
```python
@mcp.tool("sbs_pr_create", annotations=ToolAnnotations(
    title="SBS PR Create",
    readOnlyHint=False,
    idempotentHint=False,
    openWorldHint=True,
))
def sbs_pr_create(
    ctx: Context,
    title: str,
    body: Optional[str] = None,
    base: str = "main",
    draft: bool = False,
) -> PRCreateResult:
    # Auto-add ai-authored label
    # Auto-append attribution footer
    attribution = "\n\n---\n🤖 Generated with [Claude Code](https://claude.ai/code)"
    full_body = (body or "") + attribution

    cmd = ["gh", "pr", "create", "--repo", GITHUB_REPO,
           "--title", title, "--body", full_body,
           "--base", base, "--label", "ai-authored"]
    if draft:
        cmd.append("--draft")
    # ... subprocess pattern
```

---

### Wave 2: Branch Management Utilities

**Files to create:**
- [dev/scripts/sbs/core/branch_ops.py](dev/scripts/sbs/core/branch_ops.py) - Branch management

**Functions:**
```python
def create_feature_branch(slug: str, issue_number: Optional[int] = None) -> str:
    """Create and checkout feature branch.

    Naming: task/<issue>-<slug> or task/<slug>
    Returns branch name.
    """

def get_current_branch() -> str:
    """Return current branch name."""

def is_on_feature_branch() -> bool:
    """Check if we're on a feature branch (not main)."""

def push_branch(branch: str, set_upstream: bool = True) -> bool:
    """Push branch to origin."""

def delete_branch(branch: str, remote: bool = True) -> bool:
    """Delete branch locally and optionally remotely."""
```

**Integration with git_ops.py:**
- Import into existing `dev/scripts/sbs/core/git_ops.py`
- Maintain backward compatibility with existing `git_commit_and_push()`

---

### Wave 3: /task Skill PR Integration

**Files to modify:**
- [.claude/skills/task/SKILL.md](.claude/skills/task/SKILL.md)

**Changes to Phase Transitions:**

```markdown
## Phase 2: Planning

... existing content ...

**REQUIRED:** After plan approval:
1. Create feature branch: `task/<issue-or-slug>`
2. Push branch to origin
3. Create PR with:
   - Title: Task title
   - Body: Summary + link to plan
   - Labels: `ai-authored`
   - Draft: false (ready for review)
4. Transition to execution:

```bash
python3 -m sbs archive upload --trigger skill \
  --global-state '{"skill":"task","substate":"execution"}' \
  --state-transition phase_start \
  --pr-number <pr_number>
```
```

**Changes to Execution:**
- All work happens on feature branch
- Commits go to branch, not main
- Validators run against branch state

**Changes to Finalization:**
```markdown
## Phase 4: Finalization

1. Run full validation suite
2. **If gates pass:**
   - Merge PR via `sbs_pr_merge` (squash)
   - Delete feature branch
3. Update unified ledger
4. Generate summary report
5. Clear state
```

---

### Wave 4: Archive Schema Extension

**Files to modify:**
- [dev/scripts/sbs/archive/entry.py](dev/scripts/sbs/archive/entry.py)
- [dev/scripts/sbs/archive/upload.py](dev/scripts/sbs/archive/upload.py)
- [dev/scripts/sbs/cli.py](dev/scripts/sbs/cli.py)

**Schema addition:**
```python
@dataclass
class ArchiveEntry:
    # ... existing fields ...
    pr_refs: list[int] = field(default_factory=list)  # PR numbers
```

**CLI addition:**
```bash
python3 -m sbs archive upload --pr-number 42
```

**Tagging rule:**
```yaml
  - name: has-pr
    condition:
      field: pr_refs
      is_empty: false
    tags: ["has-pr"]
```

---

### Wave 5: Build Flow Adaptation

**Files to modify:**
- [dev/scripts/sbs/build/orchestrator.py](dev/scripts/sbs/build/orchestrator.py)
- [dev/scripts/sbs/build/phases.py](dev/scripts/sbs/build/phases.py)

**Changes:**
- `git_commit_and_push()` checks if on feature branch
- If on feature branch: commit/push to branch (no PR merge)
- If on main: existing behavior (for repos that don't use PRs)
- `sync_repos()` respects per-repo strategy (PR vs direct)

**Repo strategy awareness:**
```python
REPO_PR_STRATEGY = {
    "main": "pr_required",
    "toolchain/Dress": "pr_required",
    "toolchain/Runway": "pr_required",
    # ... etc
    "forks/verso": "direct",
    "forks/subverso": "direct",
    # ... etc
    "dev/storage": "direct",
}
```

---

## Critical Files

| File | Purpose |
|------|---------|
| `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_models.py` | PR Pydantic models |
| `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_tools.py` | PR MCP tools |
| `dev/scripts/sbs/core/branch_ops.py` | Branch management (new) |
| `dev/scripts/sbs/archive/entry.py` | Archive schema |
| `dev/scripts/sbs/archive/upload.py` | PR refs handling |
| `.claude/skills/task/SKILL.md` | PR workflow integration |
| `dev/scripts/sbs/build/orchestrator.py` | Branch-aware builds |

---

## Verification

1. **MCP PR tools work:**
   ```
   # Create test branch manually
   git checkout -b task/test-pr-tools
   git push -u origin task/test-pr-tools

   # Test tools
   sbs_pr_create(title="Test PR", body="Testing")
   sbs_pr_list()
   sbs_pr_get(number=<n>)
   sbs_pr_merge(number=<n>)
   ```

2. **Branch operations:**
   ```python
   from sbs.core.branch_ops import create_feature_branch
   branch = create_feature_branch("test-branch", issue_number=1)
   # Should create task/1-test-branch
   ```

3. **Full /task workflow:**
   ```
   /task #1
   # Should:
   # - Create branch task/1-verso-pdf-fix
   # - Open PR
   # - Execute on branch
   # - Merge when gates pass
   ```

---

## Gates

```yaml
gates:
  tests: all_pass
  quality:
    T1: >= 0.8
  regression: >= 0
```

---

## Execution Order

1. Wave 1 (MCP PR tools) - Foundation
2. Wave 2 (Branch ops) - Git utilities
3. Wave 3 (/task skill) - Workflow integration
4. Wave 4 (Archive schema) - PR tracking
5. Wave 5 (Build flow) - Branch awareness

Each wave validated before proceeding.
