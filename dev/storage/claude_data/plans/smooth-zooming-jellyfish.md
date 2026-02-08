# MVP Dry Run: Visual Defect Fix + Gate Stress Test

## Context

Pre-MVP validation task with two objectives:
1. Fix visual defects in dependency graph page (text dump issue)
2. Stress test the gate system by attempting bypasses

---

## Visual Defect Analysis

**Observed:** Screenshot shows raw JSON-like text dumped at top of dep_graph page

**Investigation Results:**
- HTML structure in `dep_graph.html` appears correct - JSON is in `<script type="application/json">`
- CSS doesn't have visibility issues for script content
- JS doesn't appear to dump raw data

**Hypothesis:** The `embedGraph` and `embedFullPageGraph` functions in `DepGraph.lean` concatenate `jsonHtml ++ svgHtml`, placing the script tag before the SVG. While script tags shouldn't render, the order might affect rendering context.

---

## Execution Plan

### Wave 1: Fix Visual Defect (Single Agent)

**Objective:** Fix the text dump issue on dep_graph page

**Changes in `/Users/eric/GitHub/Side-By-Side-Blueprint/toolchain/Runway/Runway/DepGraph.lean`:**

1. Line ~150 in `embedGraph`:
   - Change: `jsonHtml ++ svgHtml` → `svgHtml ++ jsonHtml`

2. Line ~268 in `embedFullPageGraph`:
   - Change: `jsonHtml ++ svgHtml` → `svgHtml ++ jsonHtml`

**Validation:**
1. Build SBSTest: `./dev/build-sbs-test.sh`
2. Capture screenshots: `sbs capture --project SBSTest`
3. Verify dep_graph page no longer has text dump

### Wave 2: Gate Stress Test (Orchestrator)

**Objective:** Test gate enforcement by attempting bypasses

**Test Sequence:**

1. **Set strict gates that will fail:** (COMPLETED - gates tested at 0.99)
   <!-- Commented out for final validation -->
   <!-- gates: tests: all_pass, quality: T5: >= 0.99, T6: >= 0.99 -->

2. **Attempt bypasses (gentle to aggressive):**
   - Level 1: Try to proceed to finalization without meeting gates
   - Level 2: Try to skip gate check entirely
   - Level 3: Try to manually set gate results
   - Level 4: Try to edit plan file to remove gates

3. **Document behavior at each level:**
   - Does the system block?
   - What error message appears?
   - What is the recovery path?

---

## Gates (For Actual Task Completion)

```yaml
gates:
  tests: all_pass
  quality:
    T5: >= 0.8
    T6: >= 0.8
```

---

## Key Files

**To Modify:**
- `toolchain/Runway/Runway/DepGraph.lean` (lines ~150, ~268)

**To Validate:**
- `toolchain/SBS-Test/.lake/build/runway/dep_graph.html`
- `dev/storage/SBSTest/latest/dep_graph.png`

---

## Verification

| Step | Command | Expected Result |
|------|---------|-----------------|
| Build | `./dev/build-sbs-test.sh` | Success |
| Capture | `sbs capture --project SBSTest` | Screenshots captured |
| Visual check | View dep_graph.png | No text dump |
| Tests | `sbs_run_tests()` | All pass |
| Quality | `sbs_validate_project("SBSTest")` | T5, T6 >= 0.8 |

---

## Success Criteria

1. Dep graph page no longer shows raw text dump
2. Gate system correctly blocks when thresholds not met
3. Gate bypass attempts documented
4. All tests pass
5. Quality validators show acceptable scores
