# Plan: Create GitHub Labels for /log Skill

**Issue:** #30
**Scope:** Add missing labels to e-vergo/Side-By-Side-Blueprint

## Task Summary

The `/log` skill requires labels for issue categorization. Add missing labels, apply them retroactively to existing issues, and update documentation.

## Execution

### Wave 1: Audit Existing Labels

1. **List all current labels**:
   ```bash
   gh label list --repo e-vergo/Side-By-Side-Blueprint --json name,description,color
   ```

2. **Report findings** before any changes

### Wave 2: Create Missing Labels

Create labels one at a time (prevents partial failure from breaking the flow):

```bash
gh label create idea -d "Idea or suggestion for consideration" --color "A333C8"
gh label create housekeeping -d "Maintenance and cleanup tasks" --color "6B7280"
```

### Labels to Create

| Label | Description | Color |
|-------|-------------|-------|
| `idea` | Idea or suggestion for consideration | `#A333C8` (purple) |
| `housekeeping` | Maintenance and cleanup tasks | `#6B7280` (gray) |

### Wave 3: Retroactive Label Application

Review existing open issues and apply appropriate labels:

1. **List open issues**:
   ```bash
   gh issue list --repo e-vergo/Side-By-Side-Blueprint --state open --json number,title,labels
   ```

2. **Apply labels** to issues that match categories but lack labels

### Wave 4: Documentation Update

Update `/log` skill documentation (`.claude/skills/log/SKILL.md`):

1. **Add `housekeeping` to type labels** (line ~172):
   - `housekeeping` - Maintenance and cleanup tasks

2. **Add keywords for type inference** (line ~36):
   - Keywords: "cleanup", "housekeeping", "refactor", "organize", "tidy", "maintenance"

3. **Update workflow options** (line ~71):
   - Add [H] Housekeeping option

## Validation

1. **Verify labels exist**:
   ```bash
   gh label list --repo e-vergo/Side-By-Side-Blueprint --json name | jq -r '.[].name' | grep -E "^(idea|housekeeping|bug|feature)$"
   ```

2. **Confirm no errors** in label list command (ensures "get all" works)

## Gates

```yaml
gates:
  tests: skip           # No code changes requiring tests
  quality: skip         # No visual/code quality impact
  regression: skip      # No functional code changes
  validation:
    - labels_exist      # All 4 labels present
    - label_list_works  # gh label list succeeds
    - docs_updated      # SKILL.md reflects label set
```

## Files Modified

- `.claude/skills/log/SKILL.md` - Document available labels

## PR Strategy

PR for documentation changes only. Label creation is GitHub API operations.
