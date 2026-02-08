# Dependency Graph Edge Routing Fix

## Status: APPROVED - Replicate Graphviz Back-Edge Handling Exactly

---

## Problem Statement

The dependency graph has a long horizontal dotted edge spanning across the graph at the same layer level. This is caused by missing back-edge handling in the Sugiyama layout.

**Screenshot:** `/Users/eric/GitHub/Side-By-Side-Blueprint/Screenshot 2026-01-27 at 8.23.54 AM.png`

---

## Root Cause

The custom Sugiyama implementation assumes the input graph is acyclic (DAG). When statement dependencies create cycles or back-edges, the layout produces incorrect routing.

**Graphviz solves this** with a pre-processing step that detects and reverses back-edges before layer assignment.

---

## Exact Graphviz Algorithm to Implement

### Step 1: Pre-Processing - Make Graph Acyclic (BEFORE Layer Assignment)

**DFS-Based Cycle Detection and Edge Reversal:**

```
function makeDagByReversal(graph):
  reversedEdges = []

  REPEAT:
    visited = {}
    recursionStack = {}
    backEdges = []

    FOR each unvisited node:
      dfsVisit(node, visited, recursionStack, graph, backEdges)

    IF backEdges is empty:
      BREAK  // Graph is now acyclic

    // Select back-edge with highest cycle participation
    edgeToReverse = selectMaxCycleEdge(backEdges)

    // Reverse it: swap from_ and to
    graph.removeEdge(edgeToReverse)
    newEdge = Edge(from_ = edgeToReverse.to, to = edgeToReverse.from_)
    newEdge.isReversed = true
    graph.addEdge(newEdge)
    reversedEdges.push(edgeToReverse)

  RETURN (graph, reversedEdges)

function dfsVisit(node, visited, recursionStack, graph, backEdges):
  IF node in visited:
    RETURN

  visited.add(node)
  recursionStack.add(node)

  FOR each outgoing edge (node → target):
    IF target NOT in visited:
      dfsVisit(target, ...)
    ELSE IF target IN recursionStack:
      // BACK EDGE FOUND - creates cycle
      backEdges.push(edge)

  recursionStack.remove(node)
```

### Step 2: Layer Assignment (Unchanged)

Run existing `assignLayers` on the now-acyclic graph. All edges point "downward" (from lower layer to higher layer).

### Step 3: Node Ordering & Coordinate Assignment (Unchanged)

Run existing barycenter heuristic and coordinate assignment.

### Step 4: Edge Routing

- **Forward edges**: Route with existing visibility graph + Dijkstra (unchanged)
- **Reversed edges**: Route the same way, but the path goes from the NEW from_ to NEW to (which is reversed)

### Step 5: Post-Processing - Restore Arrow Directions

For each reversed edge in the final SVG output:
- The **path** follows the reversed direction (enables proper routing)
- The **arrowhead** points in the **original** direction

This is done by:
1. Keeping the path points as routed
2. Reversing the path points array so it draws from original source to original target
3. Arrow marker at path end automatically points correctly

---

## Implementation Details

### File: `Dress/Dress/Graph/Layout.lean`

**Add new functions:**

```lean
/-- State for DFS cycle detection -/
structure DfsState where
  visited : HashSet String
  recursionStack : HashSet String
  backEdges : Array Edge

/-- Detect back-edges using DFS -/
partial def findBackEdgesDfs (graph : Graph) : Array Edge := ...

/-- Reverse an edge (swap from_ and to) -/
def reverseEdge (e : Edge) : Edge :=
  { e with from_ := e.to, to := e.from_, isReversed := true }

/-- Make graph acyclic by iteratively reversing back-edges -/
partial def makeAcyclic (graph : Graph) : Graph × Array Edge := ...
```

**Modify `layoutGraph` function:**

```lean
def layoutGraph (graph : Graph) (config : LayoutConfig) : LayoutGraph := do
  -- NEW: Step 0 - Make graph acyclic
  let (acyclicGraph, reversedEdges) := makeAcyclic graph

  -- Step 1: Assign layers (on acyclic graph)
  assignLayers acyclicGraph

  -- Steps 2-3: Order nodes, assign coordinates (unchanged)
  ...

  -- Step 4: Route edges (unchanged - works on acyclic graph)
  let layoutEdges := createLayoutEdges acyclicGraph ...

  -- NEW: Step 5 - Restore reversed edge directions for rendering
  let finalEdges := restoreReversedEdges layoutEdges reversedEdges

  return { nodes := ..., edges := finalEdges }
```

### File: `Dress/Dress/Graph/Types.lean`

**Add `isReversed` flag to Edge:**

```lean
structure Edge where
  from_ : String
  to : String
  style : EdgeStyle := .solid
  isReversed : Bool := false  -- NEW: track if edge was reversed for layout
```

### File: `Dress/Dress/Graph/Svg.lean`

**Handle reversed edges in rendering:**

For edges where `isReversed = true`:
- Reverse the points array before generating SVG path
- This makes the arrow point in the original direction

---

## Files to Modify

| File | Changes |
|------|---------|
| `Dress/Dress/Graph/Types.lean` | Add `isReversed : Bool` field to `Edge` |
| `Dress/Dress/Graph/Layout.lean` | Add `makeAcyclic`, `findBackEdgesDfs`, `restoreReversedEdges` |
| `Dress/Dress/Graph/Svg.lean` | Handle `isReversed` edges by reversing path points |

---

## Verification

1. Build with `./scripts/build_blueprint.sh` in SBS-Test
2. Build GCR with `./scripts/build_blueprint.sh`
3. Verify dependency graph:
   - No long horizontal crossing edges
   - Back-edges route cleanly (may curve around nodes)
   - Arrows point in correct (original) direction
4. Compare visual layout to d3-graphviz ground truth
