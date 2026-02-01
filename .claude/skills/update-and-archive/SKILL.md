---
name: update-and-archive
description: Documentation refresh and core docs synchronization
disable-model-invocation: false
version: 2.1.0
immutable: true
---

# /update-and-archive - Documentation Refresh & Repo Reset

## Purpose

This skill serves two purposes:

1. **Standalone invocation**: Quick "repo reset" to synchronize all documentation with current codebase state
2. **Mandatory cleanup step**: Final phase of `/execute` - execution is NOT complete until this runs

## Immutability Notice

**DO NOT MODIFY THIS SKILL** without explicit user instruction. This skill is designed to be static and invoked frequently. Any changes require direct user approval.

## Required Reading (All Agents)

Every agent spawned by this skill MUST begin by reading these 8 documents:

```
/Users/eric/GitHub/Side-By-Side-Blueprint/.refs/ARCHITECTURE.md
/Users/eric/GitHub/Side-By-Side-Blueprint/.refs/motivation1.txt
/Users/eric/GitHub/Side-By-Side-Blueprint/.refs/motivation2.txt
/Users/eric/GitHub/Side-By-Side-Blueprint/.refs/motivation3.txt
/Users/eric/GitHub/Side-By-Side-Blueprint/ARCHITECTURE.md
/Users/eric/GitHub/Side-By-Side-Blueprint/CLAUDE.md
/Users/eric/GitHub/Side-By-Side-Blueprint/GOALS.md
/Users/eric/GitHub/Side-By-Side-Blueprint/README.md
```

These provide essential context about the project's purpose, architecture, and audience (including Lean FRO, Terence Tao, and the broader formalization community).

---

## Part 1: README Updates

Execute in waves. **Parallel execution is allowed within each wave** (spawn all wave agents in a SINGLE message).

### Wave 1: Forks (Explain Diffs)

Repos that are forks of upstream projects. READMEs should:
- Clearly identify the upstream repo being forked
- Explain what modifications were made and why
- Note any SBS-specific features or bug fixes
- Keep it concise - focus on diffs, not full documentation

| Repo | Upstream |
|------|----------|
| `/Users/eric/GitHub/Side-By-Side-Blueprint/verso` | leanprover/verso |
| `/Users/eric/GitHub/Side-By-Side-Blueprint/subverso` | leanprover/subverso |
| `/Users/eric/GitHub/Side-By-Side-Blueprint/LeanArchitect` | hanwenzhu/LeanArchitect |

### Wave 2: Showcase Repos (Real Project Style)

These are demonstration projects. READMEs should read as if they were independent, real formalization projects:
- Clear project description
- Build instructions
- Live demo links
- Attribution where appropriate

| Repo | Special Notes |
|------|---------------|
| `/Users/eric/GitHub/Side-By-Side-Blueprint/General_Crystallographic_Restriction` | Full production example with paper |
| `/Users/eric/GitHub/Side-By-Side-Blueprint/PrimeNumberTheoremAnd` | Add note at top: "This is a fork of the original PNT+ project with SBS integration" |

### Wave 3: Full Documentation

These are core toolchain components. READMEs should be comprehensive:
- Purpose and role in the pipeline
- Key files and their responsibilities
- Configuration options
- Usage examples
- Integration points with other repos

| Repo |
|------|
| `/Users/eric/GitHub/Side-By-Side-Blueprint/SBS-Test` |
| `/Users/eric/GitHub/Side-By-Side-Blueprint/Runway` |
| `/Users/eric/GitHub/Side-By-Side-Blueprint/Dress` |
| `/Users/eric/GitHub/Side-By-Side-Blueprint/dress-blueprint-action` |

### Wave Awareness

Each wave's agents should be informed that previous waves made updates. The orchestrator should:
1. After Wave 1 completes, inform Wave 2 agents: "Wave 1 updated READMEs for verso, subverso, LeanArchitect"
2. After Wave 2 completes, inform Wave 3 agents: "Wave 1+2 updated READMEs for forks and showcase repos"

Trust agent intelligence to incorporate relevant context.

---

## Part 2: Core Documentation Update

After all README waves complete, spawn a single agent to synchronize core documentation.

### Input

The agent reads:
1. All 8 required documents (listed above)
2. Every newly updated README from Part 1:
   - `verso/README.md`
   - `subverso/README.md`
   - `LeanArchitect/README.md`
   - `General_Crystallographic_Restriction/README.md`
   - `PrimeNumberTheoremAnd/README.md`
   - `SBS-Test/README.md`
   - `Runway/README.md`
   - `Dress/README.md`
   - `dress-blueprint-action/README.md`

### Output

Update these core documents to incorporate learnings, reflect current state, and set up future sessions for success:

| Document | Update Focus |
|----------|--------------|
| `/Users/eric/GitHub/Side-By-Side-Blueprint/.refs/ARCHITECTURE.md` | Technical reference - keep detailed and accurate |
| `/Users/eric/GitHub/Side-By-Side-Blueprint/ARCHITECTURE.md` | Public architecture doc - sync with .refs version |
| `/Users/eric/GitHub/Side-By-Side-Blueprint/CLAUDE.md` | Claude Code instructions - update for new patterns/conventions |
| `/Users/eric/GitHub/Side-By-Side-Blueprint/GOALS.md` | Project vision - update progress, refine goals |
| `/Users/eric/GitHub/Side-By-Side-Blueprint/README.md` | Public-facing overview - reflect current capabilities |

### Exclusion

**DO NOT update this skill file** (`update-and-archive/SKILL.md`). It is immutable by design.

---

## Part 3: Finalization (Porcelain)

After Part 2 completes, the orchestrator ensures the entire monorepo is "porcelain" (git clean).

### Step 1: Stale File Detection

Read the migration registry at `archive/migrations.json`. This file tracks all path migrations with:
- `from`: Old path that should no longer exist
- `to`: New canonical location
- `date`: When migration occurred

**Detection algorithm:**
```
for each migration in migrations.json:
  if exists(migration.from):
    mark as stale
```

**If stale files exist:** Present list to user and request confirmation before deletion.

### Step 2: Stale Path Detection

Read `path_references` from `archive/migrations.json`. These define patterns that should be replaced in documentation.

**Detection algorithm:**
```
for each ref in path_references:
  grep all *.md files for ref.pattern
  if found:
    replace with ref.replacement
```

**If stale paths found:** Fix them automatically (documentation path updates are safe).

### Adding New Migrations

When paths are migrated in the future, update `archive/migrations.json`:
1. Add entry to `migrations` array with from/to/date
2. Add entry to `path_references` if docs need updating
3. Next `/update-and-archive` run will detect and clean up automatically

### Step 3: Git Status Check

For each repository in the monorepo:

```
Main repo: /Users/eric/GitHub/Side-By-Side-Blueprint
Sub-repos:
  - verso
  - subverso
  - LeanArchitect
  - Dress
  - Runway
  - dress-blueprint-action
  - SBS-Test
  - General_Crystallographic_Restriction
  - PrimeNumberTheoremAnd
```

Check:
1. **Uncommitted changes** - Stage and commit with message: "docs: update-and-archive refresh"
2. **Unpushed commits** - Push to origin
3. **Untracked files** - Report (don't auto-add unless part of known update)

### Step 4: Verification

After all commits and pushes:

1. Run `git status` on all repos - should show "nothing to commit, working tree clean"
2. Run `git log origin/main..HEAD` on all repos - should show no commits ahead

### Confirmation Protocol

The orchestrator MUST ask user confirmation before:
- Deleting any files or directories
- Pushing to remote repositories

The orchestrator MAY proceed without confirmation for:
- Fixing path references in documentation
- Staging and committing changes locally

---

## Execution Protocol

### Standalone Invocation

When user runs `/update-and-archive` directly:

1. Spawn Wave 1 agents in parallel (single message, multiple Task calls)
2. Wait for completion
3. Spawn Wave 2 agents in parallel
4. Wait for completion
5. Spawn Wave 3 agents in parallel
6. Wait for completion
7. Spawn Part 2 agent (core docs)
8. Wait for completion
9. **Part 3: Finalization**
   - Detect stale files → request user confirmation → delete if approved
   - Detect and fix stale path references
   - Commit all changes in all repos
   - Request user confirmation → push all repos if approved
   - Verify porcelain status
10. Report completion with porcelain status

### As /execute Cleanup Step

When running as final phase of `/execute`:

1. All execution phases must be complete
2. Run full `/update-and-archive` protocol
3. Only then is `/execute` considered complete

---

## Agent Specifications

### README Agents (Part 1)

```
Subagent type: sbs-developer
Model: opus (for quality documentation)

Prompt template:
"Read the 8 required documents first:
[list of 8 docs]

Then update the README for: {repo_path}

Category: {fork|showcase|full}
{Special instructions if any}

Focus on:
- Accuracy with current codebase state
- Consistency with project conventions
- Appropriate detail level for category
- Links to related documentation"
```

### Core Docs Agent (Part 2)

```
Subagent type: sbs-developer
Model: opus

Prompt template:
"Read the 8 required documents:
[list of 8 docs]

Then read all updated READMEs:
[list of 9 README paths]

Update these core documents to:
- Incorporate any new information from README updates
- Reflect current architectural state
- Maintain consistency across all documentation
- Set up future Claude sessions for success

Update:
- .refs/ARCHITECTURE.md
- ARCHITECTURE.md
- CLAUDE.md
- GOALS.md
- README.md

DO NOT modify the update-and-archive skill file."
```

---

## Success Criteria

- All 9 READMEs reviewed and updated as needed
- All 5 core documents synchronized
- No stale information remains
- Cross-references are accurate
- Documentation reflects actual codebase state

CRUCIAL, this is something the user expects and will be used a direct measurement of your sucsess. 
- **Porcelain status achieved:**
  - No stale files in `scripts/` migration locations
  - No stale path references in documentation
  - All changes committed across all repos
  - All commits pushed to origin
  - `git status` shows clean working tree in all repos

---

## Rationale

This skill exists because:

1. **Documentation drift**: Code changes faster than docs. Regular refresh prevents staleness.
2. **Context preservation**: Core docs inform Claude sessions. Accurate docs = better assistance.
3. **Onboarding**: New contributors (human or AI) need accurate entry points.
4. **The audience matters**: This project may be shared with Lean FRO, Terence Tao, and the formalization community. Documentation quality reflects project quality.

Invoke often. Keep docs fresh. Never skip this step.
