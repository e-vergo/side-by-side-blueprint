# Update SLS Planning + Extension Docs

Incorporate the "UI as structural enforcement" insight into both documents. The extension isn't just a frontend -- it transforms SLS principles from conventions-to-follow into properties-of-the-interface.

---

## Files

- `dev/markdowns/permanent/SLS_PLANNING.md`
- `dev/markdowns/permanent/SLS_EXTENSION.md`

---

## Step 0: ToS Compliance Analysis

### Anthropic (Claude Code)

In January 2026, Anthropic blocked third-party tools that **spoofed Claude Code's client identity** to use subscription OAuth tokens at favorable rates. The crackdown targeted tools like OpenCode that sent headers pretending to be Claude Code to access Pro/Max pricing.

**Our extension does NOT do this.** The architecture spawns the actual `claude` CLI binary as a child process. This is functionally identical to running `claude` in any terminal emulator (iTerm, Warp, Hyper). We're not:
- Spoofing client identity
- Extracting or reusing OAuth tokens
- Making direct API calls with subscription credentials
- Building a competing product

We're building a UI that runs Claude Code as-is, the same way VSCode's integrated terminal runs it. The extension is a rendering layer on top of Claude Code's own JSONL output.

**Risk area:** If Anthropic later restricts programmatic spawning of the CLI (unlikely -- it would break CI/CD use cases), the CLI backend would break. The extension API (Option 2) would be the clean path forward.

**Recommendation:** Add a note in SLS_EXTENSION.md acknowledging the distinction and stating the extension uses the official CLI binary, not credential spoofing. If distributing commercially, verify with Anthropic directly.

Sources:
- [VentureBeat: Anthropic cracks down on unauthorized Claude usage](https://venturebeat.com/technology/anthropic-cracks-down-on-unauthorized-claude-usage-by-third-party-harnesses)
- [Anthropic: Updates to consumer terms](https://www.anthropic.com/news/updates-to-our-consumer-terms)
- [Hacker News discussion](https://news.ycombinator.com/item?id=46549823)
- [Anthropic Usage Policy update](https://privacy.claude.com/en/articles/9301722-updates-to-our-acceptable-use-policy-now-usage-policy-consumer-terms-of-service-and-privacy-policy)

### VSCode Marketplace

No restrictions found on extensions that wrap CLI tools or render external process output. This is a standard pattern (e.g., GitLens wraps git, Docker extension wraps docker CLI). The marketplace terms mainly restrict extension usage to Microsoft VS Code products (not forks like VSCodium).

**Recommendation:** No issues for marketplace distribution. Standard extension.

### Action

Add a "Compliance" section to SLS_EXTENSION.md documenting:
1. The extension runs the official `claude` CLI binary (no credential extraction)
2. No API calls bypass Claude Code's managed environment
3. Commercial distribution should be verified with Anthropic
4. VSCode Marketplace: standard CLI-wrapper pattern, no restrictions

---

## SLS_PLANNING.md Changes

### 1. Fix "What SLS Is Not" (line 62)

Remove "Not a coding assistant or IDE plugin" -- it's now planned as a VSCode extension. Replace with something like "Not an IDE replacement -- it augments the editor with structured workflow."

### 2. Add extension to "What SLS Is" (after item 6, line 58)

Add item 7:

> **A VSCode extension** -- Purpose-built interface that structurally enforces the skill workflow. Four buttons map to four skills; a chat zone handles interaction; an archive plane displays entry history. The extension transforms framework conventions into interface constraints. See [SLS_EXTENSION.md](SLS_EXTENSION.md).

### 3. Update Architecture section (after line 142)

Add a subsection under Architecture referencing the extension as the primary UI layer, sitting atop the CLI/MCP/archive stack. Brief -- just establish the relationship and point to the companion doc.

### 4. Update Phases (lines 208-239)

- Phase 1: Add "Extension scaffold with skill buttons and archive plane" to deliverables
- Phase 2: The extension IS the onboarding -- "sls init" + extension activation replaces guided walkthrough
- Phase 3: Extension becomes extensible (custom skill buttons, custom chrome)

### 5. Update Open Questions (lines 245-249)

- Q1 (Package distribution): Extension is the answer for VSCode users; CLI remains for terminal users
- Q2 (MCP server packaging): Extension needs MCP access; bundle as sidecar
- Add new Q: "Claude Code programmatic API -- when/if Anthropic exposes extension-to-extension communication, swap CLI backend for native API"

---

## SLS_EXTENSION.md Changes

### 6. Add "Structural Enforcement" section (after Core Idea, before Layout)

New section capturing the analysis from our conversation. Key points:

- **Alignment through structure:** Skill buttons force intent declaration before interaction begins. The dialogue starts pre-aligned.
- **Loop visibility:** The four buttons spatially encode Work → Archive → Analyze → Improve.
- **Single-agent as physical constraint:** One chat zone, one border color, one state indicator.
- **Transparency becomes ambient:** Archive plane always visible, epochs as visual dividers.
- **Introspection promoted to peer status:** Self-improve at same visual level as Task.
- **Verification rendered:** Phase indicators make gate enforcement visible.
- **Data generation automatic:** Every interaction flows through a skill, producing structured entries.
- **Escape hatch preserves flexibility:** Raw Claude Code always available for power users.
- **Net effect:** Transforms SLS from a discipline into an environment.

### 7. Add "Orchestration Overhead Reduction" subsection

Document the specific overhead that disappears:
- No need for CLAUDE.md to enforce skill usage patterns -- the UI does it
- No need for the agent to track/display phase state -- the UI renders it
- No risk of orphaned sessions or missed archive entries -- the UI channels everything through skills
- AskUserQuestion becomes native UI rather than terminal interruption

### 8. Cross-reference from extension back to planning

Add a paragraph in "Relationship to SLS" noting that the extension resolves several open questions from SLS_PLANNING.md and changes the framework's relationship to its own principles.

---

## Verification

- Both files render correctly as markdown
- Cross-references between documents are valid
- No contradictions between the two documents
- "What SLS Is Not" no longer contradicts the extension plan
