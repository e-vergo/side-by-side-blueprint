# Loop Opportunities: Tool-Agent Interaction Patterns

Catalog of interaction loops between dev tooling, Claude Code native capabilities, and the application under development. Framework-general patterns noted; SBS-specific examples provided where concrete.

---

## Layer 1: Dev Tool <-> Dev Tool

Internal loops within the custom tooling ecosystem.

| Loop | Components | Description |
|------|-----------|-------------|
| Improvement Pipeline | Archive -> Introspect L2 -> Issues -> Task -> Archive | L1 retrospectives feed L2 analysis, which logs issues, which become tasks, which produce new L1s |
| Oracle Index | Archive entries + repo files -> Oracle compilation -> Oracle queries | Oracle indexes what exists; queries orient agents before deeper exploration |
| Quality Tracking | Build -> Validators (T1-T8) -> Quality Ledger -> Quality Delta | Each build runs validators; scores tracked over time; deltas detect regressions |
| Visual Regression | Build -> Capture -> Compliance -> Capture (loop) | Screenshot capture triggers AI compliance check; failures trigger re-capture after fixes |
| Label Lifecycle | Taxonomy YAML -> GH Label Sync -> Issue creation -> Archive tagging | Single taxonomy feeds both GitHub labels and archive tags |
| Tagging Feedback | Auto-tagger -> Tag effectiveness analysis -> Rule refinement -> Auto-tagger | Tag quality metrics inform rule updates in the next improvement cycle |

## Layer 2: Dev Tool <-> Claude Code Native

Loops where custom MCP/CLI tools interact with Claude Code's built-in capabilities.

| Loop | Components | Description |
|------|-----------|-------------|
| Agent Orchestration | Skill MCP (start/transition/end) + Task tool | Skills claim global state via MCP; orchestrator spawns Task agents that do the work |
| Context Recovery | Archive state MCP + context compaction | When Claude context compacts, first action queries archive for current state to resume |
| Progress Tracking | Archive MCP + TodoWrite | Todo items track in-session progress; archive entries track cross-session progress |
| Oracle-Assisted Search | Oracle MCP + Glob/Grep/Read | Oracle query orients to relevant files; native tools then read/search within those files |
| Issue-Driven Tasks | Issue MCP (list/get) + AskUserQuestion | Issue listing feeds into user choice; selected issue becomes task context |
| Build Monitoring | Build MCP + Bash (tail logs) | Build triggered via MCP; progress monitored via native Bash on log files |

## Layer 3: Dev Tool <-> Application Under Development

Loops where dev tools interact with the Lean/HTML/CSS application being built.

| Loop | Components | Description |
|------|-----------|-------------|
| Lean Development | Lean LSP MCP (diagnostics, goals, hover) + Edit tool | Edit Lean source -> check diagnostics -> fix errors -> re-check. LSP provides real-time feedback |
| Build Pipeline | Build script (Python) -> Lake (Lean) -> Runway (site gen) | Python orchestrates the Lean build system and HTML generation |
| Artifact Inspection | Dress (Lean) -> .lake/build/dressed/ artifacts -> Runway loading | Lean generates JSON artifacts; site generator loads them for HTML rendering |
| Screenshot QA | Browser MCP (navigate, screenshot, evaluate) -> Built site | Navigate to served site, capture screenshots, evaluate DOM elements for compliance |

## Layer 4: Claude Code Native <-> Application

Direct interaction between Claude Code's built-in tools and application code.

| Loop | Components | Description |
|------|-----------|-------------|
| Edit-Verify | Edit tool -> Lean LSP diagnostics -> Edit tool | Write Lean code, check for errors, fix until clean |
| Test-Fix | Bash (pytest/Lake) -> Read (error output) -> Edit (fix) -> Bash (re-test) | Run tests, read failures, fix code, re-run |
| Git Workflow | Bash (git) -> Read (diff) -> Edit (fix) -> Bash (commit) | Standard development cycle through version control |
| CSS Iteration | Edit (CSS) -> Build -> Browser screenshot -> Edit (CSS) | Visual iteration on styling through build-and-check |

## Layer 5: Compound Loops

Multi-layer loops that span the full stack.

| Loop | Pattern | Layers Involved |
|------|---------|-----------------|
| **Full Issue Lifecycle** | Issue logged -> /task skill claims state -> agents edit Lean/CSS -> build -> QA validates -> issue closed -> archive uploaded -> improvement cycle reads archive | 1 + 2 + 3 + 4 |
| **Visual Bug Fix** | QA finds issue -> issue logged -> agent edits CSS -> build -> capture -> compliance check -> if pass: close issue | 1 + 3 + 4 |
| **Proof Development** | Agent writes theorem -> LSP shows goals -> multi_attempt tries tactics -> edit best one -> LSP confirms -> build -> screenshot shows in site | 2 + 3 + 4 |
| **Self-Improvement Cycle** | /update-and-archive writes L1 -> /introspect 2 reads L1s -> logs issues -> /task resolves issues -> /update-and-archive writes new L1 -> cycle repeats | 1 + 2 |
| **Cross-Repo Fix** | Upstream edit (SubVerso/Verso) -> build propagates downstream (Dress/Runway) -> test/capture at project level -> commit chain through submodules | 1 + 3 + 4 |

---

## Framework-General Patterns

These patterns apply to any Claude Code + MCP setup, not just SBS:

1. **State Recovery Loop**: Any MCP server that tracks state enables context-compaction-resilient workflows. The pattern: `query state on startup -> resume from last known phase -> record state on each transition`.

2. **Tool-Assisted Search**: Custom MCP query tools (like an oracle or index) reduce the search space before Claude Code's native Glob/Grep tools do detailed exploration. Pattern: `broad MCP query -> narrow native search`.

3. **Build-Verify-Fix**: Any project with a build system benefits from: `trigger build (MCP or Bash) -> read errors (Read) -> fix (Edit) -> re-trigger`. The MCP layer adds structured build results vs raw Bash output.

4. **Archive-Driven Improvement**: Any system that records session metadata can implement: `capture session data -> analyze patterns -> generate improvements -> apply improvements -> capture new session data`. The feedback loop is the key, not the specific tools.

5. **Agent Delegation**: Task tool + MCP state tracking enables: `orchestrator plans -> delegates to agents -> agents report via MCP state changes -> orchestrator synthesizes`. Works for any project with decomposable work.
