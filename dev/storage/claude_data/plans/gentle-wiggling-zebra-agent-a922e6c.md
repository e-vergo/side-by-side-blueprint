# Plan: Simplify Modal Generation by Reusing Existing Rendering

## Analysis Summary

### Current State

**Render.lean** (`/Users/eric/GitHub/Side-By-Side-Blueprint/Runway/Runway/Render.lean`):
- `renderNode` function at line 183 takes a `NodeInfo` (from Site.lean) and produces the side-by-side HTML structure
- Generates the full `sbs-container` with `sbs-latex-column` and `sbs-lean-column`
- This is what we want to reuse in modals

**DepGraph.lean** (`/Users/eric/GitHub/Side-By-Side-Blueprint/Runway/Runway/DepGraph.lean`):
- Currently has a basic modal structure (lines 273-349) with just header/links
- `generateNodeModal` at line 324 creates minimal modals with just env type, label, and "View in Blueprint" link
- `generateStatementsContainer` at line 342 wraps all modals in `#statements` div
- Uses its own `NodeInfo` structure (lines 276-282) which is different from Site.lean's `NodeInfo`

**Key Insight**: DepGraph.lean has its OWN `NodeInfo` structure with minimal fields:
```lean
structure NodeInfo where
  id : String
  label : String
  envType : String
  url : String
```

While Site.lean has the FULL `NodeInfo` with all the HTML content fields:
```lean
structure NodeInfo where
  label : String
  title : Option String
  envType : String
  status : NodeStatus
  statementHtml : String
  proofHtml : Option String
  signatureHtml : Option String
  proofBodyHtml : Option String
  hoverData : Option String
  declNames : Array Name
  uses : Array String
  url : String
  displayNumber : Option String
```

### Data Flow

The dep-graph.json contains node data with `id`, `label`, `envType`, `url`, `status`, `leanDecls`, position info.

The manifest.json maps labels to artifact paths. Each artifact directory contains:
- `decl.tex` (with base64-encoded HTML)
- `decl.html` (full decorated code)
- `decl.hovers.json` (hover data)

Theme.lean's `generateMultiPageSite` at line 524 calls `DepGraph.fullPageGraph` which uses the dep-graph.json for modal generation but doesn't have access to the rich NodeInfo from Site.lean.

### Solution

Modify DepGraph.lean to:
1. Accept the full `Array Runway.NodeInfo` (from Site.lean) alongside the dep-graph JSON
2. Build a lookup map from node id to NodeInfo
3. For each node, call the same `renderNode` function used in Render.lean
4. Wrap that output in the modal container structure

## Implementation Steps

### Step 1: Update DepGraph.lean imports and remove duplicate NodeInfo

Add import for Site module and use its NodeInfo instead of the local one.

**File**: `/Users/eric/GitHub/Side-By-Side-Blueprint/Runway/Runway/DepGraph.lean`

Changes:
1. Add `import Runway.Site` at line 6 (after existing imports)
2. Remove the local `NodeInfo` structure definition (lines 275-282)
3. Update `parseNodeInfo` to parse into a simpler intermediate structure (just for id extraction from JSON)

### Step 2: Create a new function to generate rich modals

Add a new function `generateRichNodeModal` that:
- Takes a `Runway.NodeInfo` (the full one from Site.lean)
- Calls `renderNode` to get the sbs-container HTML
- Wraps it in the modal container structure

**Note**: `renderNode` is in `RenderM` monad, so we need to either:
- Extract it to a pure function, OR
- Run the modal generation in RenderM context

Looking at the code, `renderNode` only uses `RenderM` for `Render.getConfig` and `Render.registerHtmlId`. For modal generation, we can simplify by making a variant that doesn't need those.

Better approach: Create a pure version `renderNodeHtml` that doesn't need RenderM.

### Step 3: Update fullPageGraph signature

Change `fullPageGraph` to accept an optional `Array Runway.NodeInfo` parameter for generating rich modals.

### Step 4: Update Theme.lean call site

In `generateMultiPageSite` (line 524), pass `site.nodes` to `fullPageGraph`.

## Detailed Code Changes

### DepGraph.lean Changes

```lean
-- Add import
import Runway.Site
import Runway.Render  -- for renderNode access

-- Remove local NodeInfo structure (lines 275-282)
-- Keep only for JSON parsing purposes as a simple temp structure
private structure JsonNodeInfo where
  id : String
  label : String
  envType : String
  url : String
  deriving Inhabited

-- Rename parseNodeInfo to parseJsonNodeInfo
private def parseJsonNodeInfo ...

-- Add new function to generate modal using full NodeInfo
def generateRichNodeModal (node : Runway.NodeInfo) (nodeHtml : Html) : Html :=
  .tag "div" #[("class", "dep-modal-container"), ("id", s!"{node.label}_modal"), ("style", "display:none;")] (
    .tag "div" #[("class", "dep-modal-content")] (
      .tag "span" #[("class", "dep-closebtn")] (Html.text true "×") ++
      -- The actual sbs-container content from renderNode
      nodeHtml ++
      .tag "div" #[("class", "dep-modal-links")] (
        .tag "a" #[("class", "latex_link"), ("href", node.url)] (Html.text true "View in Blueprint →")
      )
    )
  )

-- New version of generateStatementsContainer that uses full NodeInfo
def generateStatementsContainerRich (nodes : Array Runway.NodeInfo)
    (nodeIdSet : Std.HashSet String) : RenderM Html := do
  -- Only generate modals for nodes that appear in the graph
  let graphNodes := nodes.filter (fun n => nodeIdSet.contains n.label)
  let modals ← graphNodes.mapM fun node => do
    let nodeHtml ← Runway.renderNode node
    return generateRichNodeModal node nodeHtml
  let combined := modals.foldl (· ++ ·) Html.empty
  return .tag "div" #[("id", "statements"), ("style", "display:none;")] combined

-- Update fullPageGraph signature
def fullPageGraph (svg : Option String) (json : Option String) (_projectTitle : String)
    (nodes : Option (Array Runway.NodeInfo) := none)
    (cssPath : String := "assets/blueprint.css") ...
```

### Theme.lean Changes

```lean
-- In generateMultiPageSite, around line 524
let depGraphPage := DepGraph.fullPageGraph site.depGraphSvg site.depGraphJson site.config.title (some site.nodes)
```

Wait - there's a complication. `fullPageGraph` returns `Html` directly, but `generateStatementsContainerRich` needs to be in `RenderM` to call `renderNode`.

Let me reconsider the approach...

### Revised Approach

Option A: Make fullPageGraph return IO Html and accept a render context
Option B: Create a pure version of renderNode that doesn't need RenderM
Option C: Pre-render all node HTML in Theme.lean and pass it to DepGraph

**Option C is cleanest**: In Theme.lean, before calling fullPageGraph:
1. Build a HashMap from node.label to pre-rendered HTML string
2. Pass this map to fullPageGraph
3. fullPageGraph uses the map to embed rich modal content

This way DepGraph.lean stays pure (no RenderM dependency beyond what it already has).

### Final Implementation Plan

#### DepGraph.lean Changes:

1. Keep the local `NodeInfo` structure renamed to `JsonNodeInfo` (for JSON parsing only)
2. Update `parseNodeInfo` -> `parseJsonNodeInfo`
3. Add new function:
```lean
def generateRichStatementsContainer (json : Option String)
    (nodeHtmlMap : Std.HashMap String String) : Html
```
4. Update `fullPageGraph` to accept the nodeHtmlMap parameter

#### Theme.lean Changes:

1. In `generateMultiPageSite`, before the dep graph page generation:
   - Build nodeHtmlMap by rendering each node and converting to string
   - Pass to fullPageGraph

#### Render.lean Changes:

None needed - we can call renderNode and use .asString on the result.

## Files to Modify

1. `/Users/eric/GitHub/Side-By-Side-Blueprint/Runway/Runway/DepGraph.lean`
2. `/Users/eric/GitHub/Side-By-Side-Blueprint/Runway/Runway/Theme.lean`

## Implementation Order

1. DepGraph.lean:
   - Rename NodeInfo to JsonNodeInfo (lines 275-282)
   - Update parseOneNode to use JsonNodeInfo (line 298)
   - Update parseNodeInfo to return List JsonNodeInfo (line 306)
   - Update generateNodeModal to fallback when no rich content available
   - Add generateRichNodeModal function
   - Update generateStatementsContainer to accept optional nodeHtmlMap
   - Update fullPageGraph signature to accept nodeHtmlMap

2. Theme.lean:
   - In generateMultiPageSite (around line 524), build nodeHtmlMap and pass to fullPageGraph
