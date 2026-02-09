# Crush Plan: #181, #183, #184

## Scope

| # | Title | Type | Wave |
|---|-------|------|------|
| 181 | Paper [pdf]/[html] tags on same line in sidebar | bug:visual | 1 |
| 184 | Dress artifact pipeline not generating per-declaration HTML/hover | bug:functional | 1 |
| 183 | Add `/converge hardcore [goal]` mode | feature:new | 2 |

## Wave 1: Bug Fixes (parallel, non-overlapping repos)

### Agent A: #181 — Sidebar paper link layout

**Root cause:** The `sidebar-doc-row` uses `display: flex` ([common.css:1008-1014](toolchain/dress-blueprint-action/assets/common.css#L1008-L1014)) and the Lean template creates a proper flex container ([Theme.lean:138-150](toolchain/Runway/Runway/Theme.lean#L138-L150)). Something in the parent sidebar layout or another CSS rule is causing the links to wrap.

**Fix approach:**
1. Inspect rendered sidebar via browser tools to identify the actual DOM/CSS state
2. Fix CSS (likely `flex-wrap: nowrap` or width constraint on parent `<li>`)
3. Visual verify via screenshot

**Files:** `toolchain/dress-blueprint-action/assets/common.css`

### Agent B: #184 — Dress artifact pipeline

**Root cause investigation needed.** The orchestrator at [orchestrator.py:563](dev/scripts/sbs/build/orchestrator.py#L563) calls `build_project_with_dress()` which sets `BLUEPRINT_DRESS=1` env var ([phases.py:181-193](dev/scripts/sbs/build/phases.py#L181-L193)). Yet `dressed/` dir contains only graph artifacts, not per-declaration HTML/hovers.

The agent must trace the chain:
1. Is `_build_project_internal()` actually running or skipping via lean hash cache? ([orchestrator.py:556-560](dev/scripts/sbs/build/orchestrator.py#L556-L560))
2. Does the Lean code in [ElabRules.lean](toolchain/Dress/Dress/Capture/ElabRules.lean) correctly detect `BLUEPRINT_DRESS=1`?
3. Is `writeDeclarationArtifactsFromNode` in [Declaration.lean](toolchain/Dress/Dress/Generate/Declaration.lean) getting called?
4. Are output paths resolving correctly?

**Fix approach:** Diagnose and fix the broken link in the chain above. Likely one of:
- Lean hash skip preventing dress build
- Env var not propagating to Lean elaboration hooks
- Path mismatch in artifact output

**Files:** `dev/scripts/sbs/build/orchestrator.py`, `dev/scripts/sbs/build/phases.py`, potentially `toolchain/Dress/Dress/Capture/ElabRules.lean`

**Verification:** Build SBS-Test with `--force-lake`, confirm `dressed/` contains per-declaration dirs.

## Wave 2: Feature Addition (sequential)

### Agent C: #183 — Converge hardcore mode

**Target file:** `.claude/skills/converge/SKILL.md`

**Changes:**
1. **Invocation table:** Add `| /converge hardcore GCR | Hardcore mode — no bail, tick-tock introspect |`
2. **Argument parsing:** Add `hardcore` as keyword before project name
3. **Exit conditions (lines 170-173):** In hardcore mode:
   - Disable plateau detection (condition 2)
   - Disable max_iterations cap (condition 3)
   - Keep build failure as fatal
4. **Introspect-N phase:** Add tick-tock cadence — run introspect only on ODD iterations (skip even)
5. **Recursive tick-tock for L3+:** Track L2 invocation count via archive entries, run L3 every OTHER L2 completion
6. **Safety mechanisms:** Add note about hardcore's unbounded nature + recommendation for monitoring
7. **Substates table:** Add note about variable-length iteration in hardcore mode

**No code changes** — pure skill definition update.

## Gates

```yaml
gates:
  tests: all_pass
  test_tier: evergreen
  build_verify: SBSTest --force-lake  # For #184
  visual_verify: sidebar paper links on same line  # For #181
```

## PR Strategy

Single PR on main repo. #181 touches `dress-blueprint-action` submodule (direct commit). #184 may touch `dev/scripts/` (main repo) or Dress submodule. #183 is `.claude/skills/` (main repo).

## Execution Order

1. Wave 1: Agents A (#181) and B (#184) in parallel
2. Build SBS-Test to verify #184
3. Wave 2: Agent C (#183)
4. Run evergreen tests
5. Visual verify #181 via screenshot
6. Finalize: merge PR, close issues
