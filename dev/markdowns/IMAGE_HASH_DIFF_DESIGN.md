# Image Hash Diff System - Design Document

## Overview

A deterministic visual change detection system using image hashing to complement the existing AI-based visual validation. This provides a fast, binary signal for whether screenshots have changed between captures.

---

## Problem Statement

Current visual validation relies entirely on AI vision analysis:
- **Slow**: Each page requires AI inference
- **Expensive**: Token/API costs per validation
- **Heuristic**: Results can vary between runs

Many validation scenarios only need to answer: **"Did anything change visually?"** - not "Is the change acceptable?"

---

## Proposed Solution

Add hash-based image comparison as a **pre-filter** before AI validation:

```
Screenshot Capture
       │
       ▼
   Compute Hash ──────► Store in manifest
       │
       ▼
   Compare to Baseline
       │
       ├── MATCH ────► Auto-pass (no change)
       │
       └── MISMATCH ──► Route to AI validation
```

---

## Design Decisions

### Hash Algorithm

| Option | Pros | Cons | Use Case |
|--------|------|------|----------|
| **SHA-256** (cryptographic) | Exact match, deterministic, fast | Fails on subpixel differences | Same-machine builds |
| **pHash** (perceptual) | Tolerates minor variance | Might miss subtle changes | Cross-machine comparison |
| **dHash** (difference) | Very fast, simple | Less accurate | Quick pre-check |

**Recommendation**: Use **SHA-256** as primary for same-machine workflows. Add perceptual hash as optional fallback for cross-machine scenarios.

### Storage Location

Hashes stored in capture manifest alongside screenshots:

```json
// dev/storage/SBSTest/latest/capture.json
{
  "commit": "abc123",
  "timestamp": "2026-02-01T21:00:00Z",
  "pages": {
    "dashboard": {
      "file": "dashboard.png",
      "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "phash": "d4c4b4a4949484"  // optional
    },
    "dep_graph": {
      "file": "dep_graph.png",
      "sha256": "...",
      "phash": "..."
    }
  }
}
```

### Baseline Management

**Key insight: Baseline is a pointer to an archive entry, not a separate copy.**

This eliminates duplicate storage and provides full provenance:

```
dev/storage/{project}/
├── latest/
│   ├── capture.json      # Current hashes
│   └── *.png
├── baseline.json         # Pointer to archive entry
└── archive/
    └── {date}/           # Historical captures (each has hashes)
```

**Baseline registry:**
```json
// dev/storage/SBSTest/baseline.json
{
  "current_baseline": 1769990000,  // Archive entry ID
  "history": [
    {"entry_id": 1769990000, "set_at": "2026-02-01T20:00:00Z", "reason": "validation passed"},
    {"entry_id": 1769980000, "set_at": "2026-01-31T...", "reason": "initial baseline"}
  ]
}
```

**Baseline operations:**
- `sbs baseline set` - Mark current archive entry as baseline
- `sbs baseline set --entry <id>` - Mark specific archive entry as baseline
- `sbs baseline diff` - Compare current to baseline entry
- `sbs baseline status` - Show current baseline and history

---

## CLI Integration

### New Commands

```bash
# Compute and display hashes for current screenshots
sbs hash --project SBSTest

# Compare current to baseline (or specific commit)
sbs diff --project SBSTest [--baseline <commit>]

# Set current as new baseline
sbs baseline set --project SBSTest

# Show baseline status
sbs baseline status --project SBSTest
```

### Modified Commands

```bash
# sbs capture - now auto-computes hashes
sbs capture --project SBSTest
# Output: capture.json now includes hashes

# sbs compliance - uses hash pre-filter
sbs compliance --project SBSTest
# Fast path: unchanged pages skip AI validation
```

---

## Workflow Integration

### Scenario 1: Regression Detection

CSS change to `dep_graph.css` should NOT affect dashboard:

```bash
# Before change
sbs capture --project SBSTest
sbs baseline set --project SBSTest

# After CSS change
sbs capture --project SBSTest
sbs diff --project SBSTest
# Expected: dashboard=MATCH, dep_graph=MISMATCH
```

If dashboard hash mismatches → unexpected regression detected.

### Scenario 2: Change Verification

Zebra removal task should change dashboard:

```bash
# Before change
sbs baseline set --project SBSTest

# After CSS change
sbs capture --project SBSTest
sbs diff --project SBSTest
# Expected: dashboard=MISMATCH (intentional)

# Validate the change is good
sbs compliance --project SBSTest --pages dashboard

# Promote to new baseline
sbs baseline set --project SBSTest
```

### Scenario 3: Fast Compliance

Full validation with hash pre-filter:

```bash
sbs validate-all --project SBSTest
```

Internal flow:
1. Compute current hashes
2. Compare to baseline
3. Unchanged pages → auto-pass (T0: hash match)
4. Changed pages → run AI validation (T3-T4, T7-T8)
5. Report results with distinction

### Scenario 4: Build Caching

If all page hashes match previous build, site content is identical:

```bash
python build.py --skip-if-unchanged
```

Could skip server restart, screenshot capture, etc.

---

## T1-T8 Integration

Add **T0** as deterministic pre-check:

| Test | Category | Type | Description |
|------|----------|------|-------------|
| **T0** | Visual Hash | Deterministic | Image hash matches baseline |
| T1-T2 | CLI | Deterministic | CLI execution, ledger population |
| T3-T4 | Dashboard | AI Vision | Dashboard clarity, toggle discoverability |
| T5-T6 | Design | Deterministic | Status color match, CSS variable coverage |
| T7-T8 | Polish | AI Vision | Jarring-free check, professional score |

**T0 semantics:**
- **Pass**: Hash matches baseline → no visual change
- **Fail**: Hash mismatch → visual change detected (not necessarily bad)
- **Skip**: No baseline exists

When T0 fails, route to appropriate AI test (T3-T4 or T7-T8) for assessment.

---

## Archive Integration

This is the core integration point. Hashes are stored in archive entries, enabling comparison between any two points in history.

### Archive Entry Data Model

Each archive entry includes screenshot hashes and visual diff:

```json
// Entry in archive_index.json
{
  "id": 1769998440,
  "timestamp": "2026-02-01T21:14:00Z",
  "trigger": "build",
  "project": "SBSTest",

  // NEW: Screenshot hashes
  "screenshots": {
    "dashboard": {
      "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "phash": "d4c4b4a4949484"
    },
    "dep_graph": {
      "sha256": "a1b2c3d4e5f6...",
      "phash": "e5d5c5b5a595"
    },
    "chapter": {
      "sha256": "...",
      "phash": "..."
    }
  },

  // NEW: Comparison to baseline
  "visual_diff": {
    "baseline_entry": 1769990000,
    "changed_pages": ["dashboard"],
    "unchanged_pages": ["dep_graph", "chapter"],
    "no_baseline": false
  },

  // NEW: Validation state
  "validated": true,
  "validated_at": "2026-02-01T21:20:00Z",

  // Existing fields
  "auto_tags": ["visual-changed", "pages-changed:dashboard", "css-modified"],
  "quality_scores": {...}
}
```

### Archive Upload Flow

```
sbs archive upload
       │
       ▼
   Compute hashes for current screenshots
       │
       ▼
   Load baseline entry (from baseline.json pointer)
       │
       ▼
   Compare hashes
       │
       ├── For each page:
       │   ├── Hash match → unchanged_pages.append(page)
       │   └── Hash mismatch → changed_pages.append(page)
       │
       ▼
   Generate visual_diff object
       │
       ▼
   Auto-tag based on diff results
       │
       ├── All match → "visual-unchanged"
       ├── Some differ → "visual-changed", "pages-changed:dashboard,dep_graph"
       └── No baseline → "no-baseline"
       │
       ▼
   Store entry with hashes + visual_diff + tags
```

### Auto-Tagging Rules

| Condition | Tags Applied |
|-----------|--------------|
| All pages match baseline | `visual-unchanged` |
| Some pages changed | `visual-changed`, `pages-changed:<list>` |
| No baseline exists | `no-baseline` |
| Baseline entry validated | `baseline-validated` |

Example tag: `pages-changed:dashboard,chapter` (comma-separated list)

### Query Capabilities

With hashes in every archive entry, powerful queries become possible:

| Query | Implementation |
|-------|----------------|
| "When did dashboard last change?" | Scan entries, find hash change points |
| "Diff entry X vs entry Y" | Compare screenshot hash objects |
| "All entries visually identical to baseline" | Filter by `visual-unchanged` tag |
| "Show regression point" | Find first entry where unexpected page changed |
| "Entries where only dep_graph changed" | Filter by `pages-changed:dep_graph` |

### Validation Checkpoint

Archive entries track validation state:

```
Build completes
       │
       ▼
   Archive upload (computes hashes, visual_diff)
       │
       ▼
   If visual_diff.changed_pages is empty:
       │
       └── Auto-mark validated (no changes to validate)
       │
   Else:
       │
       ▼
   Run validation on changed pages only
       │
       ├── All pass → Mark entry validated
       │   │
       │   └── Optionally: `sbs baseline set` (promote to baseline)
       │
       └── Some fail → Entry not validated, findings logged
```

**Baseline promotion flow:**
```bash
# After validation passes
sbs baseline set --project SBSTest

# This updates baseline.json to point to current entry
# Future diffs will compare against this entry
```

### Historical Analysis

With complete hash history, you can:

1. **Trace visual changes**: Plot which pages changed over time
2. **Find regression source**: Binary search through entries to find when bug appeared
3. **Verify rollback**: Confirm revert matches previous known-good state
4. **Audit trail**: Complete record of what changed and when

---

## Archive Tagging

Auto-tags based on hash comparison (applied during archive upload):

| Condition | Tags |
|-----------|------|
| All pages match baseline | `visual-unchanged` |
| Some pages changed | `visual-changed`, `pages-changed:<list>` |
| No baseline exists | `no-baseline` |
| Entry passed validation | `validated` |

---

## Implementation Phases

### Phase 1: Hash Computation (MVP)
- Add hash computation to `sbs capture`
- Store SHA-256 and optional pHash in `capture.json`
- `sbs hash --project <name>` command to display current hashes

### Phase 2: Archive Entry Enhancement
- Add `screenshots` field to archive entries (hash per page)
- Compute hashes during `sbs archive upload`
- Store in `archive_index.json` entries

### Phase 3: Baseline Registry
- Create `baseline.json` per project
- `sbs baseline set` - point to archive entry
- `sbs baseline status` - show current baseline info

### Phase 4: Visual Diff Integration
- Add `visual_diff` field to archive entries
- Compare to baseline during archive upload
- Auto-tag: `visual-unchanged`, `visual-changed`, `pages-changed:<list>`

### Phase 5: Compliance Fast Path
- Hash pre-filter in `sbs compliance`
- T0 metric: hash match = auto-pass
- Skip AI validation for unchanged pages
- Report distinct results (hash-pass vs AI-pass)

### Phase 6: Query & Analysis Tools
- `sbs diff --entry <id1> --entry <id2>` - compare any two entries
- `sbs history --page dashboard` - show change points for a page
- Filter archive by visual change tags

---

## Edge Cases

### Rendering Variance
Font rendering, antialiasing, and subpixel differences can cause hash mismatches even when visually identical.

**Mitigation:**
- Use perceptual hash (pHash) for cross-machine comparison
- Document that SHA-256 is for same-machine only
- Consider image normalization (resize, grayscale) before hashing

### Dynamic Content
Timestamps, random IDs, or animation frames cause false mismatches.

**Mitigation:**
- Capture at consistent state (after animations complete)
- Document known dynamic elements
- Consider masking regions for hash computation

### Large Images
SHA-256 is fast, but very large images add latency.

**Mitigation:**
- Current screenshots are ~200-300KB (acceptable)
- Monitor performance as image count grows

---

## Success Criteria

1. `sbs capture` produces hashes in `capture.json`
2. Archive entries include `screenshots` and `visual_diff` fields
3. `sbs baseline set/status` manages baseline pointer correctly
4. `sbs diff` correctly identifies changed/unchanged pages
5. Archive auto-tags: `visual-unchanged`, `visual-changed`, `pages-changed:<list>`
6. `sbs compliance` skips AI validation for unchanged pages (T0 fast path)
7. Can query archive for visual change history
8. False positive rate < 1% (same-machine, SHA-256)

---

## Open Questions

1. **Per-branch baselines?** Should each git branch have its own baseline, or is global sufficient?
2. **Perceptual hash threshold**: What Hamming distance threshold for pHash means "similar enough"? (Typically 5-10)
3. **Automatic baseline promotion**: Should validation pass automatically promote to baseline, or require explicit `sbs baseline set`?
4. **Archive entry retention**: Should old entries be pruned, or keep full history? (Storage implications)
5. **Cross-project baselines**: Should there be a "meta-baseline" across all projects for full-stack validation?

---

## References

- [perceptual hashing](https://www.hackerfactor.com/blog/index.php?/archives/432-Looks-Like.html) - pHash algorithm
- [imagehash Python library](https://github.com/JohannesBuchner/imagehash) - Implementation option
- Current capture code: `dev/scripts/sbs/capture/`
- Current compliance code: `dev/scripts/sbs/tests/compliance/`
