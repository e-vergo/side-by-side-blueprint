---
name: finalize-docs
description: Update all READMEs and reference documentation after plan completion
disable-model-invocation: true
---

# Documentation Finalization Workflow

Execute this workflow at plan completion to update all documentation across the Side-by-Side Blueprint monorepo.

## Writing Guidelines (apply to all agents)

- Tone: Professional technical documentation for world-class computer scientists and mathematicians
- Purpose: Inform and document, not promote or sell
- Avoid vacuous statements that sound impressive but lack substance
- Useful to both humans and AI systems reading the repo
- Trust the repo; investigate if context clashes with code

## Execution Instructions

**CRITICAL: Execute waves sequentially. Within each wave, spawn all agents in a SINGLE message with multiple Task tool calls to run them in parallel.**

---

## Wave 1: Fork Repos (3 parallel agents)

Spawn these 3 agents IN PARALLEL (single message, multiple tool calls):

### Agent 1: subverso README
**Repository:** `/Users/eric/GitHub/Side-By-Side-Blueprint/subverso`

Task: Update README for this fork. Include clear attribution to original SubVerso project at top. Analyze git history/diffs to document all fork modifications (InfoTable O(1) lookups, caches, error handling). Trust the code.

### Agent 2: verso README
**Repository:** `/Users/eric/GitHub/Side-By-Side-Blueprint/verso`

Task: Update README for this fork. Include attribution to original Verso project. Document SBSBlueprint genre, VersoPaper genre, rainbow bracket implementation. Trust the code.

### Agent 3: LeanArchitect README
**Repository:** `/Users/eric/GitHub/Side-By-Side-Blueprint/LeanArchitect`

Task: Update README. Document @[blueprint] attribute options, 6-status color model, dependency inference. Trust the code.

**After Wave 1 completes:** Commit all changes with message "docs: update fork READMEs (Wave 1)"

---

## Wave 2: Core Tooling (4 parallel agents)

**Prerequisites:** Wave 1 must complete first. Each agent reads Wave 1 READMEs before writing.

Spawn these 4 agents IN PARALLEL:

### Agent 1: Runway README
**Repository:** `/Users/eric/GitHub/Side-By-Side-Blueprint/Runway`
**Read first:** subverso, verso, LeanArchitect READMEs

Task: Update README. Document CLI commands, runway.json config, output structure, paper/PDF generation.

### Agent 2: Dress README
**Repository:** `/Users/eric/GitHub/Side-By-Side-Blueprint/Dress`
**Read first:** subverso, verso, LeanArchitect READMEs

Task: Update README. Document artifact format, manifest schema, Sugiyama algorithm, validation checks.

### Agent 3: dress-blueprint-action README
**Repository:** `/Users/eric/GitHub/Side-By-Side-Blueprint/dress-blueprint-action`
**Read first:** subverso, verso, LeanArchitect READMEs

Task: Update README. Document GitHub Action inputs/outputs, 4-file CSS architecture, JS features.

### Agent 4: SBS-Test README
**Repository:** `/Users/eric/GitHub/Side-By-Side-Blueprint/SBS-Test`
**Read first:** subverso, verso, LeanArchitect READMEs

Task: Update README. Document test coverage, node inventory, template usage instructions.

**After Wave 2 completes:** Commit with message "docs: update core tooling READMEs (Wave 2)"

---

## Wave 3: Showcase Repos (2 parallel agents)

**Prerequisites:** Waves 1 and 2 must complete first.

Spawn these 2 agents IN PARALLEL:

### Agent 1: GCR README
**Repository:** `/Users/eric/GitHub/Side-By-Side-Blueprint/General_Crystallographic_Restriction`
**Read first:** All Wave 1 and Wave 2 READMEs

Task: Update README as standalone mathematical project. Document theorem, project structure, live site.

### Agent 2: PNT README
**Repository:** `/Users/eric/GitHub/Side-By-Side-Blueprint/PrimeNumberTheoremAnd`
**Read first:** All Wave 1 and Wave 2 READMEs

Task: **PRESERVE original content.** Add SBS Fork section at TOP explaining this is a fork, what SBS features it showcases (591 nodes), toolchain dependencies. Keep all original content below separator.

**After Wave 3 completes:** Commit with message "docs: update showcase READMEs (Wave 3)"

---

## Final: Reference Documentation (1 agent)

**Prerequisites:** All waves must complete first.

Spawn 1 agent:

**Files to update:**
- `/Users/eric/GitHub/Side-By-Side-Blueprint/.refs/ARCHITECTURE.md`
- `/Users/eric/GitHub/Side-By-Side-Blueprint/.claude/agents/sbs-developer.md`
- `/Users/eric/GitHub/Side-By-Side-Blueprint/CLAUDE.md`

**Required reading:**
1. All 10 READMEs (including `/Users/eric/GitHub/Side-By-Side-Blueprint/README.md`)
2. Current plan file
3. `/Users/eric/GitHub/Side-By-Side-Blueprint/.refs/GOALS.md`
4. Current state of files being updated
5. Motivation docs: `.refs/motivation1.txt`, `.refs/motivation2.txt`, `.refs/motivation3.txt`

Task: Update reference docs to reflect current repository state. Document the repo exactly as it exists now. Do NOT include development history, changes, or removed features. Set future agents up for success with accurate context.

**After Final completes:** Commit with message "docs: update reference documentation"

---

## Error Handling

If an agent fails:
1. Retry the failed repo once
2. If retry fails, continue with remaining repos
3. Report all failures at workflow end

---

## Summary Report

After all waves complete, provide:
- Wave completion status (✓ or ✗ per repo)
- Files modified
- Commits created
- Any failures encountered
