# Fix: Remove zebra striping from blueprint CSS (#307)

## Context
Side-by-side proof displays have inconsistent backgrounds on even-numbered theorem blocks. Zebra striping changes the container background, but `pre.lean-code` overrides it back to `--sbs-bg-surface`, causing a mismatch between left (LaTeX) and right (Lean) panels.

## Changes

### `blueprint.css` (`Side-By-Side-Blueprint/toolchain/dress-blueprint-action/assets/`)
1. **Remove** zebra striping block (lines 246-252): comment + `section:has(...)` rule
2. **Remove** `background-color: var(--sbs-bg-surface);` from the `.sbs-signature pre.lean-code, .sbs-proof-lean pre.lean-code` rule (line 258) -- only existed to counteract zebra

### `common.css` (`Side-By-Side-Blueprint/toolchain/dress-blueprint-action/assets/`)
1. **Remove** `--sbs-zebra-even: #ebebeb;` from light mode `:root` (line 120)
2. **Remove** `--sbs-zebra-even: #252525;` from dark mode `[data-theme="dark"]` (line 350)
3. **Clean up** zebra reference in comment (line 24)

## Verification
- Build SBS-Test (`./dev/build-sbs-test.sh`)
- Visually confirm all theorem blocks have uniform backgrounds
