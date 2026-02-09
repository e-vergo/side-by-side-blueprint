# Plan: Verify SBS-Test Cycle Detection

## Analysis Summary

The current SBS-Test cycle setup in `/Users/eric/GitHub/Side-By-Side-Blueprint/SBS-Test/SBSTest/StatusDemo.lean` appears correct:

```lean
@[blueprint "thm:cycleA"
  (uses := ["thm:cycleB"])]
theorem cycleA : True := trivial

@[blueprint "thm:cycleB"
  (uses := ["thm:cycleA"])]
theorem cycleB : True := trivial
```

This creates mutual dependencies:
- `thm:cycleA` depends on `thm:cycleB`
- `thm:cycleB` depends on `thm:cycleA`

Both endpoints are valid `@[blueprint]` labels, so edges should NOT be filtered out.

## Data Flow Verification

1. **Attribute parsing** (`Attribute.lean:76-78`): String literals like `"thm:cycleB"` go to `usesLabels`
2. **NodePart creation** (`Attribute.lean:248-249`): `cfg.usesLabels` flows to `NodePart.usesLabels`
3. **Edge inference** (`Output.lean:61`): `part.usesLabels` added to inferred uses
4. **Graph building** (`Build.lean:300-307`): `fromEnvironment` uses `node.inferUses`
5. **Edge filtering** (`Build.lean:51`): Only filters if endpoint not in `labelToId`

## Hypothesis

The cycle setup is correct. The issue might be:
1. An old cached manifest from before the fix
2. Different code path being exercised
3. Inspection of wrong output file

## Steps to Verify

1. Build Dress and SBS-Test fresh
2. Check the generated `manifest.json` for `checkResults.cycles`
3. If empty, add debug tracing to understand why

## No Changes Needed

After analysis, the current StatusDemo.lean already has a valid cycle using proper `@[blueprint]` labels and `uses` attributes. The test should work with a clean build.
