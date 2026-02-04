# Strange Loop Station (SLS) -- Planning Document

## Vision

Strange Loop Station is a lightweight, general-purpose framework for **arbitrary recursive self-improvement**. It provides the scaffolding for humans and agentic AI to design, execute, and analyze structured feedback loops -- then improve the loops themselves.

The core insight: a disciplined archive process, combined with automated tooling built around the rhythm it creates, enables the construction of extraordinarily powerful feedback loops. The archive becomes both the record and the raw material for improvement. Each cycle generates structured data that feeds the next cycle. The loops compound.

This idea has surfaced repeatedly throughout the development history of the SBS project -- an emergent pattern that kept reasserting itself across different contexts. Hence the name: a strange loop, where the system's output becomes its input, and the process of improvement becomes the subject of improvement.

## Principles

### Alignment Through Dialogue (Primary)

The human and the agent negotiate direction through structured conversation. Plans are proposed, questioned, revised, and approved before execution. Alignment is not assumed -- it is actively constructed and maintained through every interaction. The dialogue itself is the alignment mechanism.

### Supporting Values

- **Transparency:** Archives are public-facing by design. Every decision, every cycle, every outcome is visible and auditable. There is no hidden state.
- **Verification:** Claims are checked. Improvements are measured. Gates enforce quality thresholds before phase transitions. Trust is earned through evidence, not assertion.
- **Introspection:** The system examines its own behavior. Self-improvement skills analyze past sessions, identify patterns, surface what worked and what didn't. The agent is expected to practice metacognition.
- **Improvement:** The default posture is "this can be better." Every cycle is an opportunity to refine not just the work product but the process that produced it.
- **Generality:** The framework imposes no domain. Self-improvement loops for software, writing, research, operations, learning -- the archive and skill machinery is domain-agnostic.
- **Flexibility:** The framework adapts to the user. Configuration over convention. Pluggable validators, configurable quality dimensions, extensible skill definitions.

### One Working Agent at a Time (Architectural Invariant)

A single implementation agent executes at any given moment. This is not a limitation -- it is a deliberate design choice that provides:

- **Oversight:** The orchestrator (human or top-level chat) always knows what is happening and can intervene
- **Collision avoidance:** No conflicting edits, no merge conflicts between parallel agents, no race conditions on shared state
- **Traceability:** Every change maps to exactly one agent invocation with a clear scope and mandate
- **Debuggability:** When something goes wrong, there is exactly one place to look
- **Archive coherence:** Each archive entry corresponds to a single, well-defined unit of work

Read-only exploration agents may run in parallel for research and context gathering. But writes are serialized through the single implementation agent.

---

## What SLS Is

A starter repository that provides:

1. **An archive system** -- Structured entries, epochs, state machine, auto-tagging, session data extraction, and gate validation. The archive is the backbone: it records what happened, enables analysis of what worked, and feeds forward into future cycles.

2. **A skill system** -- Phase-based workflows with state machine transitions. Ships with four core skills:
   - `/task` -- Structured task execution (alignment -> planning -> execution -> finalization -> archive)
   - `/self-improve` -- Recursive analysis of past sessions to surface improvement opportunities
   - `/log` -- Quick capture of bugs, features, and ideas to GitHub Issues
   - `/update-and-archive` -- Epoch-closing documentation refresh and porcelain state

3. **An orchestration model** -- CLAUDE.md + agent definitions that encode the single-agent architecture, user preferences, and project conventions. The orchestrator coordinates; agents implement.

4. **A CLI** -- Command-line tooling for archive management, status monitoring, testing, and oracle compilation. The interface through which humans interact with the archive outside of agent sessions.

5. **An MCP server** -- Machine-callable tools for skill state management, archive queries, self-improvement analysis, GitHub integration, and test execution. The interface through which agents interact with the archive during sessions.

6. **A test framework** -- Pluggable validator architecture with tier-based test execution (evergreen / dev / temporary). Gates enforce quality thresholds at phase transitions.

7. **A VSCode extension** -- Purpose-built interface that structurally enforces the skill workflow. Four skill buttons, a chat zone, and an archive plane replace free-form terminal interaction with a UI that channels behavior through the framework's intended patterns. The extension transforms conventions into interface constraints -- the principles described above become properties of the environment rather than rules to remember. See [SLS_EXTENSION.md](SLS_EXTENSION.md).

## What SLS Is Not

- Not an IDE replacement -- it augments the editor with structured workflow
- Not domain-specific (no Lean, no math, no particular language)
- Not a multi-agent swarm framework
- Not an autonomous agent -- the human is always in the loop via dialogue

---

## The Self-Improvement Loop

The fundamental cycle:

```
Work -> Archive -> Analyze -> Improve -> Work (better)
```

### Basic Loop (ships out of the box)

1. **Do work** via `/task` -- structured phases with gate validation
2. **Archive** via `/update-and-archive` -- capture entry, auto-tag, close epoch
3. **Reflect** via `/self-improve` -- analyze entries since last improvement cycle
4. **Apply findings** -- update CLAUDE.md, skills, agent definitions, tooling
5. Return to step 1 with accumulated improvements

### Meta Loop (enabled by the archive)

The self-improvement skill itself can be improved:

1. Run N basic self-improvement cycles
2. Analyze the last N `/self-improve` entries as a corpus
3. Ask: What patterns did self-improvement find? What did it miss? What changed as a result? Did those changes actually help?
4. Update the self-improvement skill definition, analysis heuristics, or tagging rules
5. Run N more cycles with the improved self-improvement process
6. Repeat

This is where the strange loop closes: the improvement process improves itself using its own output as input.

### Data Generation

Every SLS instance running publicly on GitHub produces structured, timestamped, tagged archive entries. Across many instances, this becomes a corpus of well-documented data about recursive self-improvement -- what strategies different users and agents tried, what worked, what didn't, how loops evolved over time. The standardized archive format makes this data comparable and aggregatable.

---

## Architecture

### Repository Structure

```
sls/                          # Root
  .claude/
    CLAUDE.md                 # Orchestration config + user preferences
    agents/
      sls-developer.md        # Implementation agent definition
      sls-oracle.md           # Auto-generated concept index
    skills/
      task/SKILL.md           # Structured task execution
      self-improve/SKILL.md   # Recursive self-improvement
      log/SKILL.md            # Quick issue capture
      update-and-archive/SKILL.md  # Epoch closing
  cli/
    sls/                      # Python CLI package
      archive/                # Archive management (entries, index, upload, tagging, gates)
      tests/
        pytest/               # Test suite with tier markers
        validators/           # Pluggable validator framework
      oracle/                 # Concept index compilation
      cli.py                  # Entry point
  mcp/                        # MCP server
    tools/                    # Tool implementations
      skill_tools.py          # State machine operations
      archive_tools.py        # Archive queries
      analysis_tools.py       # Self-improvement analytics
      github_tools.py         # Issue/PR management
      test_tools.py           # Test execution
  config/
    sls.json                  # Project configuration (repo paths, quality dimensions, sync targets)
    tags.yaml                 # Auto-tagging rules
    gates.yaml                # Phase transition gates
  storage/
    archive/                  # Archive entries and index
    sessions/                 # Claude Code session data
```

### Configuration-Driven Design

Domain-specific values that are hardcoded in SBS become configuration in SLS:

```json
{
  "project": {
    "name": "my-project",
    "repos": {},
    "root_detection": "sls.json"
  },
  "quality": {
    "dimensions": [],
    "validators": {}
  },
  "archive": {
    "sync_target": null,
    "public": true
  },
  "github": {
    "repo": "owner/repo",
    "issue_labels": ["bug", "feature", "idea"],
    "area_labels": []
  }
}
```

Users define their own quality dimensions, validators, repo topology, and sync targets. The framework provides the machinery; the user provides the domain.

### Extension Layer

The VSCode extension sits atop the CLI/MCP/archive stack as the primary user interface:

```
┌──────────────────────────┐
│   VSCode Extension       │  Skill buttons, chat zone, archive plane
├──────────────────────────┤
│   Claude Code CLI        │  Session management, CLAUDE.md, permissions
├──────────────────────────┤
│   MCP Server + CLI       │  Skill state, archive queries, GitHub, tests
├──────────────────────────┤
│   Archive + Config       │  Entries, index, sls.json, gates, tags
└──────────────────────────┘
```

The extension communicates downward: it spawns Claude Code sessions (which use MCP tools internally) and reads archive state directly. It never writes to the archive or manages skill state itself -- all mutations flow through Claude Code sessions. Terminal users bypass the top layer and interact with Claude Code + CLI directly. See [SLS_EXTENSION.md](SLS_EXTENSION.md) for the full spec.

---

## Transfer Plan from SBS

### Transfers As-Is (rename sbs -> sls)
- Archive entry model, index, session data extraction, auto-tagging engine
- Skill state machine (start, transition, end), phase enforcement
- Gate parsing and evaluation framework
- Validator plugin architecture (base class, registry, discovery)
- Test infrastructure (tier markers, fixtures, CLI runner)
- Archive invariant tests (immutability, schema, single-skill, phase ordering, epoch semantics)
- Self-improvement analysis tools (session mining, comparative analysis, system health, user patterns)
- GitHub integration (issues, PRs -- parameterized by repo)

### Needs Generalization
- Archive upload flow -- extract hardcoded repo paths into config
- Skill definitions -- remove SBS-specific tool references, validator names, build commands
- CLI entry point -- rename package, update help text
- MCP tool registration -- rename tools, update descriptions
- Root detection -- replace SBS heuristic with sls.json presence check
- Quality gates -- replace T1-T8 with configurable dimension names
- Oracle compilation -- generalize source paths

### Drop Entirely
- All Lean LSP tools (18 tools)
- Visual testing subsystem (capture, compare, compliance, screenshot history)
- Zulip integration
- SBS build pipeline (build.py, project-specific build scripts)
- 6-status color model
- Verso/SubVerso/LeanArchitect/Dress/Runway domain knowledge

---

## Phases

### Phase 1: Extract and Generalize

Create the SLS repository with the core loop working end-to-end:

- Archive system with configurable project identity
- Four core skills ported and generalized
- CLI with archive management commands
- MCP server with skill, archive, analysis, and GitHub tools
- sls.json configuration schema
- Evergreen test suite passing
- CLAUDE.md template with orchestration model and preference sections
- Single example project demonstrating one complete improvement cycle
- Extension scaffold: skill buttons, chat zone (CLI backend), archive plane with epoch dividers

### Phase 2: Onboarding and Documentation

Make it usable by someone who isn't us:

- `sls init` command that scaffolds a new project
- Interactive configuration wizard (quality dimensions, GitHub repo, sync target)
- Extension activation as the primary onboarding path -- installing the extension and opening a project replaces the guided walkthrough
- Minimal README focused on "install extension, init, run your first loop"

### Phase 3: Extensibility

Make it powerful for advanced users:

- Custom skill authoring guide and template
- Custom validator authoring with the plugin registry
- Tagging rule authoring
- Gate configuration for custom quality dimensions
- Meta-self-improvement tooling (analyze N past improvement cycles)
- Archive export/aggregation utilities for cross-instance analysis
- Extension extensibility: custom skill buttons, custom per-skill chrome, pluggable archive row renderers

---

## Open Questions

1. **Package distribution:** VSCode extension for IDE users; CLI remains for terminal users. PyPI for the Python backend? Bundled with the extension?
2. **MCP server packaging:** Extension needs MCP access for archive reads. Bundle as sidecar process or call Python tools directly via child process?
3. **Archive format versioning:** How to handle schema evolution as the framework matures without breaking existing archives?
4. **Multi-project support:** Should one SLS installation support multiple projects, or is it one SLS instance per project? Extension: one instance per VSCode window?
5. **Sync targets:** iCloud is SBS-specific. What general sync mechanisms should SLS support? Git-native (push to a branch)? Cloud storage? None (local only)?
6. **Claude Code programmatic API:** The extension currently spawns `claude` CLI as a child process. If Anthropic exposes extension-to-extension communication, swap the CLI backend for the native API. Monitor their roadmap.
