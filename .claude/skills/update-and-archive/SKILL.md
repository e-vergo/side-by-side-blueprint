---
name: update-and-archive
description: Documentation refresh and porcelain state
version: 3.0.0
---

# /update-and-archive

Update all documentation and achieve porcelain git state across all repos.

---

## Required Reading

Agents must read these before making changes:

```
/Users/eric/GitHub/Side-By-Side-Blueprint/dev/.refs/ARCHITECTURE.md
/Users/eric/GitHub/Side-By-Side-Blueprint/dev/.refs/motivation1.txt
/Users/eric/GitHub/Side-By-Side-Blueprint/dev/.refs/motivation2.txt
/Users/eric/GitHub/Side-By-Side-Blueprint/dev/.refs/motivation3.txt
/Users/eric/GitHub/Side-By-Side-Blueprint/dev/.refs/motivation4.txt
/Users/eric/GitHub/Side-By-Side-Blueprint/dev/markdowns/ARCHITECTURE.md
/Users/eric/GitHub/Side-By-Side-Blueprint/CLAUDE.md
/Users/eric/GitHub/Side-By-Side-Blueprint/dev/markdowns/GOALS.md
/Users/eric/GitHub/Side-By-Side-Blueprint/dev/markdowns/README.md
```

---

## Trigger Semantics

The `sbs archive upload` command accepts a `--trigger` flag for provenance tracking:

| Trigger | Source | Purpose |
|---------|--------|---------|
| `--trigger build` | Automatic from `build.py` | Marks entry as build-triggered |
| `--trigger skill` | This skill (Part 4) | Marks entry as skill-triggered |
| Manual (no flag) | User CLI invocation | Marks as manual |

**Key**: Trigger affects metadata only, not behavior. Archive upload always does the same thing regardless of trigger source.

---

## Part 0: README Staleness Check

Run the staleness check to determine which repos need documentation updates:

```bash
cd /Users/eric/GitHub/Side-By-Side-Blueprint/dev/scripts
python3 -m sbs readme-check --json
```

**Interpret the JSON output:**
- `repos_with_changes` array lists repos with uncommitted/unpushed changes
- `changed_files` shows what was modified in each repo
- `clean_repos` array lists repos needing no updates

**Agent allocation based on `summary.needs_review`:**
- 0 repos changed → Skip Part 1 entirely
- 1-2 repos changed → Single agent for all README updates
- 3-5 repos changed → 2 agents (grouped by wave)
- 6+ repos changed → 3 agents (one per wave)

**Only update READMEs for repos appearing in `repos_with_changes`.**

---

## Part 1: README Updates

### Wave Dependencies

Updates must respect this order (earlier waves inform later ones):

1. **Forks** - Explain diffs from upstream
   - `forks/verso` (upstream: leanprover/verso)
   - `forks/subverso` (upstream: leanprover/subverso)
   - `forks/LeanArchitect` (upstream: hanwenzhu/LeanArchitect)

2. **Showcase** - Real project style with build instructions
   - `showcase/General_Crystallographic_Restriction`
   - `showcase/PrimeNumberTheoremAnd` (note: fork of original PNT+)

3. **Toolchain** - Comprehensive documentation
   - `toolchain/SBS-Test`
   - `toolchain/Runway`
   - `toolchain/Dress`
   - `toolchain/dress-blueprint-action`

### Agent Strategy

The orchestrator decides agent count based on git state:
- Check `git diff` and `git status` across all repos
- Few changes → fewer agents (possibly one for all)
- Many changes → more agents (grouped by wave)
- Small code changes may still require many doc updates

---

## Part 2: Core Documentation

After READMEs are updated, synchronize:

| Document | Focus |
|----------|-------|
| `dev/.refs/ARCHITECTURE.md` | Technical reference |
| `dev/markdowns/ARCHITECTURE.md` | Public architecture |
| `CLAUDE.md` | Claude Code instructions |
| `dev/markdowns/GOALS.md` | Project vision |
| `dev/markdowns/README.md` | Public overview |

**Exclusion:** Do not modify this skill file.

---

## Part 3: Oracle Regeneration

**Timing**: Oracle regeneration happens AFTER all README waves complete in Part 1, and AFTER core documentation sync in Part 2. This ensures the Oracle captures the final state of all documentation.

Regenerate the Oracle:

```bash
cd /Users/eric/GitHub/Side-By-Side-Blueprint/dev/scripts
python3 -m sbs oracle compile
```

This extracts content from all READMEs and CLAUDE.md into `.claude/agents/sbs-oracle.md`.

**Validation:**
- Oracle must have all sections populated
- File paths must be valid

---

## Part 4: Finalization

### Stale Detection

Read `dev/storage/migrations.json`:
- Delete files listed in `migrations[].from` if they exist (confirm with user)
- Replace patterns in `path_references` automatically

### Archive Integration

Archive upload runs automatically during builds. If this skill is invoked after a build, session data has already been archived. For standalone documentation refreshes, run:

```bash
cd /Users/eric/GitHub/Side-By-Side-Blueprint/dev/scripts
sbs archive upload --trigger skill
```

### Git Porcelain

For each repo (main + 10 submodules):

```
Main: /Users/eric/GitHub/Side-By-Side-Blueprint
Submodules:
  - forks/verso, forks/subverso, forks/LeanArchitect
  - toolchain/Dress, toolchain/Runway, toolchain/SBS-Test, toolchain/dress-blueprint-action
  - showcase/General_Crystallographic_Restriction, showcase/PrimeNumberTheoremAnd
  - dev/storage
```

1. Stage and commit changes: `"docs: update-and-archive refresh"`
2. Request user confirmation before pushing
3. Verify: `git status` clean, no commits ahead of origin

---

## Success Criteria

- Documentation reflects codebase state
- All repos committed and pushed
- `git status` clean in all 11 repos
