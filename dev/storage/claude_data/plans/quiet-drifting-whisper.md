# Issue #297: Blueprint Dashboard Button in VSCode Infoview

## Context

Add a button to the Blueprint infoview panel that triggers the SBS build pipeline and opens the generated dashboard in a VSCode webview tab. This is a **community-facing** feature -- no SLS/Python dependency. Everything runs through Lake.

**Repo:** `Side-By-Side-Blueprint/forks/vscode-lean4/` (branch: `sbs/blueprint-panel`)

---

## Architecture

```
blueprintPanel.tsx                    vscode-lean4 extension
┌──────────────────────┐              ┌──────────────────────────────┐
│ "Open Dashboard" link│──command:──> │ BlueprintDashboardProvider    │
│  (command: URI)      │    URI       │  ├─ detectProject()          │
└──────────────────────┘              │  ├─ checkRunwayConfig()      │
                                      │  ├─ runBuild() [4 steps]    │
                                      │  └─ openWebview()            │
                                      └──────────────┬───────────────┘
                                                     │
                                      ┌──────────────▼───────────────┐
                                      │ Dashboard WebviewPanel       │
                                      │  - Loads Runway HTML from    │
                                      │    .lake/build/runway/       │
                                      │  - Rewrites asset paths via  │
                                      │    asWebviewUri()            │
                                      │  - Intercepts link clicks    │
                                      │    for in-webview navigation │
                                      └──────────────────────────────┘
```

**Key design decisions:**
- **command: URI** for button (no EditorApi changes needed; `enableCommandUris: true` is already set)
- **CDN allowed** via permissive CSP (MathJax, jQuery, Tippy.js, Popper.js, Marked)
- **Skip build** if `.lake/build/runway/index.html` exists; offer Rebuild button
- **Page navigation** via injected click interceptor script + postMessage to extension

---

## Build Pipeline (No SLS)

From project root, 4 sequential Lake commands:
```bash
lake build                                    # Compile + capture artifacts
lake build +:blueprint                        # Blueprint facets (module.json, manifest)
lake exe dress extract_blueprint graph        # Dependency graph layout
lake exe runway build runway.json             # Generate static HTML site
```

Output: `.lake/build/runway/` (16 HTML files + `assets/` directory)

Requires: `runway.json` in project root (fail-fast if absent).

---

## Waves

### Wave 1: Build Runner + Command Registration

**New file:** `vscode-lean4/src/blueprintBuild.ts`
- `hasRunwayConfig(projectRoot)` -- check for `runway.json`
- `hasBuildOutput(projectRoot)` -- check for `.lake/build/runway/index.html`
- `getRunwayDir(projectRoot)` -- resolve output path
- `runBlueprintBuild(projectRoot, channel)` -- execute 4-step pipeline with `window.withProgress()` showing step count (1/4, 2/4...)
- Use `batchExecuteWithProgress()` pattern from `batch.ts` or direct `child_process` execution

**Modify:** `vscode-lean4/package.json`
- Add `lean4.blueprint.openDashboard` command under category "Lean 4: Blueprint"
- Add `when` clause: `lean4.isLeanFeatureSetActive`
- Add to command palette menus

**Modify:** `vscode-lean4/src/extension.ts`
- Instantiate `BlueprintDashboardProvider` alongside existing providers

**Patterns to follow:**
- [projectoperations.ts](vscode-lean4/src/projectoperations.ts) -- command registration + project detection
- [batch.ts](vscode-lean4/src/utils/batch.ts) -- `batchExecuteWithProgress()` for shell execution with progress
- [projectInfo.ts](vscode-lean4/src/utils/projectInfo.ts) -- `findLeanProjectRootInfo()` for project root detection

### Wave 2: Dashboard Webview

**New file:** `vscode-lean4/src/blueprintDashboard.ts`
- `BlueprintDashboardProvider` class (implements `Disposable`)
- Creates `WebviewPanel` with:
  - `enableScripts: true`, `retainContextWhenHidden: true`, `enableFindWidget: true`
  - `localResourceRoots: [Uri.file(runwayDir)]`
- `transformHtml(html)` pipeline:
  1. Rewrite `./assets/*` references to `asWebviewUri()` paths
  2. Inject CSP meta tag (allow `cspSource` + CDN domains for script/style/font/connect)
  3. Inject navigation interceptor script (`acquireVsCodeApi()` + click listener on `<a>` tags)
  4. Leave external links (`http://...`) and anchors (`#...`) untouched
- `loadPage(page)` -- read HTML from disk, transform, set `webview.html`
- `onDidReceiveMessage` handler for `{type: 'navigate', page}` and `{type: 'rebuild'}`
- Page history stack for back-navigation

**CSP policy:**
```
default-src 'none';
img-src ${cspSource} data:;
style-src ${cspSource} 'unsafe-inline' https://unpkg.com;
script-src ${cspSource} 'unsafe-inline' https://cdn.jsdelivr.net https://code.jquery.com https://unpkg.com;
font-src ${cspSource} https://cdn.jsdelivr.net;
connect-src https://cdn.jsdelivr.net https://unpkg.com;
```

**Patterns to follow:**
- [loogleview.ts](vscode-lean4/src/loogleview.ts) -- CSP meta tag, `webviewUri()` helper
- [manualview.ts](vscode-lean4/src/manualview.ts) -- local file loading, link normalization
- [infoview.ts](vscode-lean4/src/infoview.ts) -- `createWebviewPanel()` lifecycle

### Wave 3: Blueprint Panel Button

**Modify:** `lean4-infoview/src/infoview/blueprintPanel.tsx`
- Add "Open Dashboard" link at bottom of panel using `command:lean4.blueprint.openDashboard` URI
- Show always (not gated on blueprint data presence) -- dashboard is a project-level action

**Modify:** `lean4-infoview/src/infoview/index.css`
- Minimal styles: link color from VS Code theme vars, top border separator, hover underline

### Wave 4: Polish

**Modify:** `vscode-lean4/src/blueprintDashboard.ts`
- Rebuild button: inject a small toolbar header into the HTML with "Rebuild" action
- Anchor scrolling: when navigating to `page.html#fragment`, inject `scrollIntoView()` script
- Title updates: `webviewPanel.title` reflects current page
- PDF link handling: intercept `.pdf` links, open via `vscode.env.openExternal()`
- Error states: build failure notification with output channel link

---

## Files Summary

| Action | File |
|--------|------|
| **Create** | `vscode-lean4/src/blueprintBuild.ts` |
| **Create** | `vscode-lean4/src/blueprintDashboard.ts` |
| **Modify** | `vscode-lean4/src/extension.ts` |
| **Modify** | `vscode-lean4/package.json` |
| **Modify** | `lean4-infoview/src/infoview/blueprintPanel.tsx` |
| **Modify** | `lean4-infoview/src/infoview/index.css` |

---

## Risk Areas

1. **CSP + MathJax**: MathJax dynamically loads sub-resources. May need additional CSP entries discovered during testing.
2. **HTML transform regex**: Brittle if Runway output format changes. Acceptable given stable, known output.
3. **`acquireVsCodeApi()` singleton**: Injected script calls this once. Safe since Runway HTML doesn't call it, but fragile if that changes.
4. **Large pages (PNT dep graph)**: 591-node SVG. Should render fine in webview but needs perf check.

---

## Verification

Each wave verified with:
1. **VSCode MCP tools** (`get_diagnostics`, `execute_command`) for TypeScript compilation and runtime checks
2. **Manual testing** in the extension host:
   - Open SBS-Test project in VSCode
   - Navigate to a `@[blueprint]` declaration
   - Verify button appears in infoview
   - Click button -> build runs with progress -> dashboard opens
   - Navigate between pages (dashboard, chapters, dep graph)
   - Test command palette access (`Ctrl+Shift+P` -> "Open Blueprint Dashboard")
3. **Edge cases**: missing `runway.json`, no build output, build failure, non-Lean project
