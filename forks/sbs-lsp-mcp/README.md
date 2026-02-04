# sbs-lsp-mcp

SBS-enhanced Lean LSP MCP Server. A fork of [lean-lsp-mcp](https://github.com/nomen/lean-lsp-mcp) that adds 41 SBS-specific tools and 3 Zulip browsing tools while preserving all 18 Lean proof-writing capabilities.

## Overview

This package extends the upstream lean-lsp-mcp with SBS-specific tools for:

- **Oracle querying**: Query the SBS Oracle for file locations and concept information
- **Archive inspection**: Inspect orchestration state, epoch summaries, and entry history
- **Context generation**: Build formatted context blocks for agent injection
- **Testing tools**: Run pytest suites and T1-T8 validators
- **Build tools**: Trigger project builds and manage dev servers
- **Investigation tools**: View screenshots, visual history, and search archive entries
- **GitHub integration**: Create, list, get, close issues and manage pull requests; agent-optimized issue logging
- **Self-improve analysis**: Mine session patterns, analyze skill lifecycle, detect interruptions
- **Question analysis**: Extract and aggregate AskUserQuestion interactions from sessions
- **Skill management**: Start, transition, end, fail, and handoff skill sessions with global state tracking
- **Zulip browsing**: Search and browse Leanprover Zulip anonymously via browser automation

## Installation

```bash
# From the monorepo root
cd forks/sbs-lsp-mcp
uv pip install -e .

# Or with pip
pip install -e .

# With dev dependencies
uv pip install -e ".[dev]"
```

## Usage

### As MCP Server

```bash
# Start the server (stdio transport - default)
sbs-lsp-mcp

# With HTTP transport
sbs-lsp-mcp --transport streamable-http --port 8000

# With local loogle (avoids rate limits, ~5-10 min first-time install)
sbs-lsp-mcp --loogle-local
```

### Claude Code Configuration

Add to `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "sbs-lsp": {
      "command": "uv",
      "args": ["run", "--directory", "/Users/eric/GitHub/Side-By-Side-Blueprint/forks/sbs-lsp-mcp", "sbs-lsp-mcp"]
    }
  }
}
```

Or if globally installed:

```json
{
  "mcpServers": {
    "sbs-lsp": {
      "command": "sbs-lsp-mcp",
      "env": {
        "LEAN_PROJECT_PATH": "/path/to/your/lean/project"
      }
    }
  }
}
```

## Tools (62 Total)

### Lean Tools (18)

All upstream Lean tools are preserved for proof-writing workflows:

| Tool | Description |
|------|-------------|
| `lean_build` | Build project and restart LSP |
| `lean_file_contents` | Get file contents (deprecated) |
| `lean_file_outline` | Get imports and declarations |
| `lean_diagnostic_messages` | Get compiler diagnostics |
| `lean_goal` | Get proof goals at position (MOST IMPORTANT) |
| `lean_term_goal` | Get expected type at position |
| `lean_hover_info` | Get type signature and docs |
| `lean_completions` | Get IDE autocompletions |
| `lean_declaration_file` | Get declaration source file |
| `lean_multi_attempt` | Try multiple tactics |
| `lean_run_code` | Run code snippet |
| `lean_local_search` | Fast local declaration search |
| `lean_leansearch` | Natural language search (mathlib) |
| `lean_loogle` | Type pattern search (mathlib) |
| `lean_leanfinder` | Semantic search by meaning |
| `lean_state_search` | Find lemmas for goal |
| `lean_hammer_premise` | Get premises for automation |
| `lean_profile_proof` | Profile theorem performance |

### SBS Tools (41)

#### Core (12)

Tools for Side-by-Side Blueprint development workflows:

| Tool | Description |
|------|-------------|
| `sbs_oracle_query` | Query the SBS Oracle for file/concept info |
| `sbs_archive_state` | Get current orchestration state |
| `sbs_epoch_summary` | Get epoch statistics |
| `sbs_context` | Build context block for agents |
| `sbs_run_tests` | Run pytest suite |
| `sbs_validate_project` | Run T1-T8 validators |
| `sbs_build_project` | Trigger project build |
| `sbs_serve_project` | Manage dev server |
| `sbs_last_screenshot` | Get latest screenshot for a page |
| `sbs_visual_history` | View screenshot history |
| `sbs_search_entries` | Search archive entries |
| `sbs_inspect_project` | Prepare context for agent-driven visual QA |

#### GitHub Issues (6)

| Tool | Description |
|------|-------------|
| `sbs_issue_create` | Create a new issue with full label taxonomy support |
| `sbs_issue_log` | Agent-optimized issue logging with auto-populated archive context |
| `sbs_issue_list` | List issues with state/label filters |
| `sbs_issue_get` | Get details of a specific issue by number |
| `sbs_issue_close` | Close an issue with optional comment |
| `sbs_issue_summary` | Aggregate statistics for all open issues |

#### GitHub PRs (4)

| Tool | Description |
|------|-------------|
| `sbs_pr_create` | Create a pull request from the current branch |
| `sbs_pr_list` | List PRs with state/label filters |
| `sbs_pr_get` | Get details of a specific PR by number |
| `sbs_pr_merge` | Merge a PR (squash/rebase/merge strategies) |

#### Self-Improve Analysis (11)

Tools for mining session data and analyzing agent behavior. The first 6 provide foundational analysis; the last 5 (added in [#65](https://github.com/e-vergo/Side-By-Side-Blueprint/issues/65)) add targeted diagnostics for skill lifecycle, phase transitions, interruptions, gate failures, and tag noise.

| Tool | Description |
|------|-------------|
| `sbs_analysis_summary` | Aggregate archive statistics (entries, triggers, quality, tags) |
| `sbs_entries_since_self_improve` | All entries since last self-improve invocation |
| `sbs_successful_sessions` | Mine sessions with completed tasks and high quality |
| `sbs_comparative_analysis` | Compare approved vs rejected plans |
| `sbs_system_health` | Build metrics, quality coverage, archive friction |
| `sbs_user_patterns` | Alignment efficiency and communication patterns |
| `sbs_skill_stats` | Per-skill invocation count, completion rate, duration |
| `sbs_phase_transition_health` | Detect backward transitions and skipped phases |
| `sbs_interruption_analysis` | Detect user corrections and redirections |
| `sbs_gate_failures` | Gate failure rates, overrides, and common failure types |
| `sbs_tag_effectiveness` | Auto-tag signal-to-noise ratio analysis |

#### Question Analysis (2)

| Tool | Description |
|------|-------------|
| `sbs_question_analysis` | Extract AskUserQuestion interactions from Claude Code sessions |
| `sbs_question_stats` | Aggregate question usage statistics by skill and header |

#### Skill Management (6)

| Tool | Description |
|------|-------------|
| `sbs_skill_status` | Check active skill, phase, and whether a new skill can start |
| `sbs_skill_start` | Claim global state for a skill session |
| `sbs_skill_transition` | Move to a new phase within the active skill |
| `sbs_skill_end` | Release global state, ending the skill session |
| `sbs_skill_fail` | Record skill failure with reason and release global state |
| `sbs_skill_handoff` | Atomic end-one-start-another skill transition |

### Zulip Tools (3)

Tools for browsing Leanprover Zulip anonymously (requires `ZULIP_ENABLED=1`):

| Tool | Description |
|------|-------------|
| `zulip_search` | Search messages across streams/topics |
| `zulip_fetch_thread` | Fetch complete thread content as markdown |
| `zulip_screenshot` | Capture screenshot of a Zulip thread |

## SBS Tool Details

### Oracle Tools

#### `sbs_oracle_query`

Query the SBS Oracle for file locations and concept information.

```python
# Find where graph layout is implemented
sbs_oracle_query(query="graph layout")
# Returns: Dress/Graph/Layout.lean

# Find status color model
sbs_oracle_query(query="status color")
# Returns: documentation about 6-status color model
```

### Archive Tools

#### `sbs_archive_state`

Get current orchestration state from the archive.

```python
sbs_archive_state()
# Returns: global_state, last_epoch_entry, entries_in_current_epoch, etc.
```

#### `sbs_epoch_summary`

Get aggregate statistics for an epoch.

```python
# Current epoch
sbs_epoch_summary()

# Specific epoch
sbs_epoch_summary(epoch_entry_id="20260201120000")
```

#### `sbs_context`

Build a formatted context block for agent injection.

```python
# All sections
sbs_context()

# Specific sections
sbs_context(include=["state", "epoch"])
```

### Testing Tools

#### `sbs_run_tests`

Run pytest suite and return structured results.

```python
# Run all tests
sbs_run_tests()

# Run with filter
sbs_run_tests(filter="test_color")

# Run specific path
sbs_run_tests(path="sbs/tests/pytest/validators")
```

#### `sbs_validate_project`

Run T1-T8 validators on a project.

```python
# Default validators (T5, T6)
sbs_validate_project(project="SBSTest")

# Specific validators
sbs_validate_project(project="GCR", validators=["T5", "T6", "T7"])
```

### Build Tools

#### `sbs_build_project`

Trigger build.py for a project.

```python
# Full build
sbs_build_project(project="SBSTest")

# Dry run
sbs_build_project(project="SBSTest", dry_run=True)
```

#### `sbs_serve_project`

Manage local dev server.

```python
# Check status
sbs_serve_project(project="SBSTest", action="status")

# Start server
sbs_serve_project(project="SBSTest", action="start", port=8000)

# Stop server
sbs_serve_project(project="SBSTest", action="stop")
```

### Investigation Tools

#### `sbs_last_screenshot`

Get most recent screenshot for a page.

```python
sbs_last_screenshot(project="SBSTest", page="dashboard")
# Returns: image_path, captured_at, hash
```

#### `sbs_visual_history`

View screenshot history for a page.

```python
sbs_visual_history(project="SBSTest", page="dep_graph", limit=5)
# Returns: list of entries with hashes for change detection
```

#### `sbs_search_entries`

Search archive entries by various criteria.

```python
# By project
sbs_search_entries(project="GCR")

# By tags
sbs_search_entries(tags=["build", "visual-change"])

# Combined filters
sbs_search_entries(project="SBSTest", trigger="build", limit=10)
```

### Zulip Tools

**Note:** Zulip tools require `ZULIP_ENABLED=1` and Playwright to be installed:

```bash
pip install sbs-lsp-mcp[zulip]
playwright install chromium
```

#### `zulip_search`

Search Zulip messages across streams.

```python
# Simple search
zulip_search(query="SubVerso")

# Stream-scoped search
zulip_search(query="tactic", stream="lean4")

# Topic-scoped search
zulip_search(query="apply", stream="lean4", topic="Metaprogramming", limit=50)
```

#### `zulip_fetch_thread`

Fetch complete thread content as structured data.

```python
# Fetch thread messages
zulip_fetch_thread(stream="lean4", topic="Metaprogramming")
# Returns: messages, participants, date range

# With limit
zulip_fetch_thread(stream="mathlib4", topic="PR reviews", limit=100)
```

#### `zulip_screenshot`

Capture screenshot of a Zulip thread.

```python
# Capture to latest/
zulip_screenshot(stream="lean4", topic="Metaprogramming")

# Capture with archiving
zulip_screenshot(stream="lean4", topic="Metaprogramming", archive=True)

# Full page capture
zulip_screenshot(stream="lean4", topic="Metaprogramming", full_page=True)
# Returns: image_path, url, hash, captured_at
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `LEAN_PROJECT_PATH` | Default Lean project path |
| `LEAN_LOOGLE_LOCAL` | Enable local loogle (`true`/`false`) |
| `LEAN_LOOGLE_CACHE_DIR` | Override loogle cache location |
| `LEAN_LOG_LEVEL` | Logging level (`INFO`, `DEBUG`, `NONE`) |
| `LEAN_LSP_MCP_TOKEN` | Optional auth token |
| `SBS_ROOT` | Side-by-Side Blueprint monorepo root |
| `ZULIP_ENABLED` | Enable Zulip tools (`true`/`false`) |
| `ZULIP_URL` | Zulip instance URL (default: `https://leanprover.zulipchat.com`) |

## Development

```bash
# Install dev dependencies
uv pip install -e ".[dev]"

# Run tests
uv run pytest tests/ -v

# Run specific test file
uv run pytest tests/test_oracle_tools.py -v
```

### Test Structure

```
tests/
  test_oracle_tools.py      # Oracle query tests
  test_archive_tools.py     # Archive state/epoch/context tests
  test_build_tools.py       # Build/validate/serve tests
  test_visual_tools.py      # Screenshot/history tests
  test_search_tools.py      # Entry search tests
```

## License

MIT License - see [LICENSE](LICENSE)

## Acknowledgments

Based on [lean-lsp-mcp](https://github.com/nomen/lean-lsp-mcp) by the original authors.
