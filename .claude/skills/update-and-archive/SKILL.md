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
/Users/eric/GitHub/Side-By-Side-Blueprint/ARCHITECTURE.md
/Users/eric/GitHub/Side-By-Side-Blueprint/CLAUDE.md
/Users/eric/GitHub/Side-By-Side-Blueprint/GOALS.md
/Users/eric/GitHub/Side-By-Side-Blueprint/README.md
```

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
| `ARCHITECTURE.md` | Public architecture |
| `CLAUDE.md` | Claude Code instructions |
| `GOALS.md` | Project vision |
| `README.md` | Public overview |

**Exclusion:** Do not modify this skill file.

---

## Part 3: Finalization

### Stale Detection

Read `dev/storage/migrations.json`:
- Delete files listed in `migrations[].from` if they exist (confirm with user)
- Replace patterns in `path_references` automatically

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
