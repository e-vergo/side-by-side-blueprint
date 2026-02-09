# Zulip Browsing Tools for sbs-lsp-mcp

## Summary

Add three MCP tools to browse Leanprover Zulip anonymously via Playwright:
- `zulip_search` - Search messages across streams
- `zulip_fetch_thread` - Fetch complete thread content as markdown
- `zulip_screenshot` - Capture screenshot to archive

## Architecture Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Tool granularity | 3 separate tools | Clear single-purpose tools |
| State management | Stateless per call | Simpler, no session cleanup |
| Browser lifecycle | Shared instance via lifespan | Avoids 2-3s cold start per call |
| Screenshot storage | Archive pattern | Matches existing `dev/storage/` |
| Enable flag | `ZULIP_ENABLED` env var | Opt-in, no overhead when disabled |

## Files to Modify

| File | Changes |
|------|---------|
| `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/server.py` | Add browser to `AppContext`, modify `app_lifespan()`, conditional registration |
| `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_models.py` | Add 4 Pydantic models |
| `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/sbs_utils.py` | Add Zulip storage path helpers |
| `forks/sbs-lsp-mcp/src/sbs_lsp_mcp/zulip_tools.py` | **NEW**: All tool implementations |
| `forks/sbs-lsp-mcp/pyproject.toml` | Add playwright optional dependency |

## Implementation Waves

### Wave 1: Models and Storage (no browser)

1. Add Pydantic models to `sbs_models.py`:
   - `ZulipMessage` - Single message with sender, content, timestamp
   - `ZulipSearchResult` - Search results with messages, count, filters
   - `ZulipThreadResult` - Thread with messages, participants, dates
   - `ZulipScreenshotResult` - Screenshot path, url, hash, metadata

2. Add storage utilities to `sbs_utils.py`:
   - `ZULIP_ARCHIVE_DIR = ARCHIVE_DIR / "zulip"`
   - `get_zulip_screenshot_path(stream, topic)`
   - `_sanitize_filename(name)`

### Wave 2: Browser Lifecycle

1. Modify `AppContext` dataclass:
   ```python
   browser: "Browser | None" = None
   browser_context: "BrowserContext | None" = None
   ```

2. Modify `app_lifespan()`:
   - Check `ZULIP_ENABLED` env var
   - Launch Playwright Chromium (headless)
   - Create browser context with 1920x1080 viewport
   - Add `"zulip": []` to rate_limit dict
   - Cleanup in finally block

3. Add conditional registration after `register_sbs_tools(mcp)`:
   ```python
   if os.environ.get("ZULIP_ENABLED", "").lower() in ("1", "true", "yes"):
       register_zulip_tools(mcp)
   ```

### Wave 3: Tool Implementations

Create `zulip_tools.py` with:

**`zulip_search`**
- Params: `query`, `stream?`, `topic?`, `limit=20`
- Builds Zulip narrow URL with search
- Extracts messages via JS evaluation
- Returns `ZulipSearchResult`

**`zulip_fetch_thread`**
- Params: `stream`, `topic`, `limit=50`
- Navigates to stream/topic narrow
- Scrolls to load more messages
- Returns `ZulipThreadResult`

**`zulip_screenshot`**
- Params: `stream`, `topic`, `archive=False`, `full_page=False`
- Captures screenshot to `dev/storage/zulip/latest/`
- Optionally copies to archive with timestamp
- Writes `capture.json` metadata
- Returns `ZulipScreenshotResult`

### Wave 4: Dependencies and Docs

1. Update `pyproject.toml`:
   ```toml
   [project.optional-dependencies]
   zulip = ["playwright>=1.40.0"]
   ```

2. Add usage example to README

## Storage Structure

```
dev/storage/zulip/
├── latest/
│   ├── thread_lean4_Metaprogramming.png
│   └── capture.json
└── archive/
    └── 2026-02-02_10-30-15/
        ├── thread_lean4_Metaprogramming.png
        └── capture.json
```

## Gates

```yaml
gates:
  tests: all_pass
  quality:
    T1: >= 1.0    # CLI execution (these tools don't affect existing validators)
  regression: >= 0
```

## Verification

1. **Unit test**: Run with `ZULIP_ENABLED=1`, call each tool
2. **Manual test**:
   ```bash
   # Start MCP server with Zulip enabled
   ZULIP_ENABLED=1 python -m sbs_lsp_mcp

   # Test via Claude Code or MCP client
   zulip_search(query="SubVerso")
   zulip_fetch_thread(stream="lean4", topic="Metaprogramming")
   zulip_screenshot(stream="lean4", topic="Metaprogramming", archive=True)
   ```
3. **Check screenshot**: Read returned `image_path` to verify capture
