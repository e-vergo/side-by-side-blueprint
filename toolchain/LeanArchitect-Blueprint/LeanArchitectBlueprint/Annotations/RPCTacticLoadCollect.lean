import Architect

open Architect

namespace LeanArchitectBlueprint.Annotations

-- === Architect.RPC ===

attribute [blueprint "la:blueprint-info"
  (keyDeclaration := true)
  (title := "Blueprint Info")
  (statement := /-- The data transfer object returned by the RPC endpoint to the VS Code
  infoview panel. Provides a projection of the full \texttt{Node} record into
  the subset of fields needed for live editor feedback.

  Fields include the Lean constant name, LaTeX label, derived status string,
  statement and proof text, dependency list, and dashboard metadata
  (\texttt{keyDeclaration}, \texttt{message}, \texttt{above}, \texttt{below}).
  All string-typed fields default to the empty string; the dependency array
  defaults to empty. This ensures the infoview always receives a well-formed
  JSON payload even for minimally annotated declarations.

  \uses{la:node, la:node-status} -/)
  (proof := /-- A flat structure with 11 fields, deriving \texttt{FromJson},
  \texttt{ToJson}, and \texttt{Inhabited} for RPC serialization. -/)
  (uses := ["la:node", "la:node-status"])]
  Architect.BlueprintInfo

-- === Architect.Tactic ===

attribute [blueprint "la:proof-doc-string-state"
  (title := "Proof DocString State")
  (statement := /-- The persistent state type for the proof docstring environment extension.
  Maps declaration names to arrays of docstring fragments, enabling multiple
  tactic-level docstrings per declaration to be accumulated and later
  concatenated.

  Defined as $\texttt{SMap Name (Array String)}$, a staged map that
  supports both in-module accumulation and cross-module import merging. -/)
  (proof := /-- An abbreviation for \texttt{SMap Name (Array String)}. -/)
  (uses := ["la:node"])]
  Architect.ProofDocString.State

attribute [blueprint "la:proof-doc-string-entry"
  (title := "Proof DocString Entry")
  (statement := /-- The entry type for the proof docstring environment extension.
  A pair of (declaration name, docstring text) that is fed to the
  \texttt{SimplePersistentEnvExtension} accumulator.

  Each entry represents a single \texttt{/-- ... -/} comment preceding a
  tactic in a proof block. -/)
  (proof := /-- An abbreviation for \texttt{Name $\times$ String}. -/)]
  Architect.ProofDocString.Entry

attribute [blueprint "la:add-proof-doc-string"
  (title := "Add Proof DocString")
  (statement := /-- Registers a proof docstring for a given declaration name in the
  environment extension.

  Called by the \texttt{tacticDocComment} elaborator whenever a
  \texttt{/-- ... -/} comment appears before a tactic in a proof block.
  The docstring is associated with the enclosing declaration via
  \texttt{Term.getDeclName?} and stored for later retrieval during
  LaTeX output generation.

  \uses{la:proof-doc-string-entry} -/)
  (proof := /-- Delegates to \texttt{proofDocStringExt.addEntry} with the
  declaration name as the async declaration key. -/)
  (uses := ["la:proof-doc-string-entry"])]
  Architect.addProofDocString

attribute [blueprint "la:get-proof-doc-string"
  (title := "Get Proof DocString")
  (statement := /-- Retrieves all accumulated proof docstrings for a declaration,
  concatenated with double-newline separators.

  This function is the read-side counterpart to \texttt{addProofDocString}.
  It queries the \texttt{proofDocStringExt} persistent environment extension
  and joins all fragments into a single string. The result is used as the
  default proof text when no explicit \texttt{proof := ...} option is
  provided in the \texttt{@[blueprint]} attribute.

  \uses{la:proof-doc-string-state, la:add-proof-doc-string} -/)
  (proof := /-- Looks up the name in the extension state, retrieves the
  \texttt{Array String} (defaulting to empty), converts to a list,
  and intercalates with \texttt{"\\n\\n"}. -/)
  (uses := ["la:proof-doc-string-state", "la:add-proof-doc-string"])]
  Architect.getProofDocString

-- === Architect.Load ===

attribute [blueprint "la:env-of-imports"
  (title := "Environment of Imports")
  (statement := /-- Reconstructs a Lean \texttt{Environment} from an array of module names
  by importing them into a fresh environment.

  This is the entry point for offline analysis: given a list of module names
  (e.g., from a lakefile target), it calls \texttt{importModules} with
  \texttt{leakEnv := true} and \texttt{loadExts := true} to obtain a fully
  initialized environment containing all declarations, environment extensions,
  and compiled code from those modules.

  Adapted from \texttt{DocGen4.envOfImports}. Requires
  \texttt{enableInitializersExecution} for modules that register parsers
  via \texttt{initialize}. -/)
  (proof := /-- Calls \texttt{Lean.enableInitializersExecution} (unsafe) then
  \texttt{importModules} with the given module names. -/)]
  Architect.envOfImports

attribute [blueprint "la:run-env-of-imports"
  (title := "Run Environment of Imports")
  (statement := /-- Executes a \texttt{CoreM} computation against an environment built from
  the given module imports, with configurable Lean options.

  Initializes the search path, constructs the environment via
  \texttt{envOfImports}, then runs the monadic action in a \texttt{Core.Context}
  with a high heartbeat limit and kernel typechecking disabled for performance.
  This is the standard wrapper for batch-mode blueprint extraction.

  \uses{la:env-of-imports} -/)
  (proof := /-- Builds a \texttt{Core.Context} with \texttt{maxHeartbeats := 100000000},
  \texttt{debug.skipKernelTC := true}, and \texttt{Elab.async := false},
  then converts the \texttt{CoreM} action to \texttt{IO} via \texttt{toIO}. -/)
  (uses := ["la:env-of-imports"])]
  Architect.runEnvOfImports

attribute [blueprint "la:latex-output-of-import-module"
  (title := "LaTeX Output of Imported Module")
  (statement := /-- Produces the complete LaTeX output (header file and per-node artifacts)
  for a single imported module.

  Composes \texttt{runEnvOfImports} with \texttt{moduleToLatexOutput} to
  load the module's environment and extract all blueprint nodes into their
  LaTeX representations. This is the primary entry point for the
  \texttt{extract\_blueprint} CLI command's per-module processing.

  \uses{la:run-env-of-imports} -/)
  (proof := /-- Calls \texttt{runEnvOfImports} with a singleton array containing the
  module name, passing \texttt{moduleToLatexOutput} as the \texttt{CoreM} action. -/)
  (uses := ["la:run-env-of-imports"])]
  Architect.latexOutputOfImportModule

attribute [blueprint "la:json-of-import-module"
  (title := "JSON of Imported Module")
  (statement := /-- Produces the JSON representation of all blueprint content for a single
  imported module.

  Parallel to \texttt{latexOutputOfImportModule} but outputs structured JSON
  instead of LaTeX. Used by downstream tools (Dress, Runway) that consume
  blueprint metadata programmatically rather than through TeX compilation.

  \uses{la:run-env-of-imports} -/)
  (proof := /-- Calls \texttt{runEnvOfImports} with \texttt{moduleToJson} as the
  \texttt{CoreM} action. -/)
  (uses := ["la:run-env-of-imports"])]
  Architect.jsonOfImportModule

-- === Architect.CollectUsed ===

attribute [blueprint "la:collect-used-context"
  (title := "CollectUsed Context")
  (statement := /-- The reader context for the dependency collection traversal.

  Carries two fields:
  \begin{itemize}
    \item \texttt{env}: the Lean \texttt{Environment} to query for constant info
    \item \texttt{root}: the name of the declaration being analyzed, used to
          avoid self-referential cycles in the traversal
  \end{itemize} -/)
  (proof := /-- A two-field structure used as the reader component of
  the \texttt{CollectUsed.M} monad. -/)]
  Architect.CollectUsed.Context

attribute [blueprint "la:collect-used-state"
  (title := "CollectUsed State")
  (statement := /-- The mutable state for the dependency collection traversal.

  Maintains:
  \begin{itemize}
    \item \texttt{visited}: a \texttt{NameSet} of constants already processed,
          preventing infinite loops in the presence of mutual recursion
    \item \texttt{used}: an accumulator array of constant names identified as
          blueprint dependencies or axioms
  \end{itemize} -/)
  (proof := /-- A two-field structure with defaults (\texttt{visited := \{\}},
  \texttt{used := \#[]}), used as the state component of the
  \texttt{CollectUsed.M} monad. -/)
  (uses := ["la:collect-used-context"])]
  Architect.CollectUsed.State

attribute [blueprint "la:collect-used-monad"
  (title := "CollectUsed Monad")
  (statement := /-- The monad stack for dependency collection: a \texttt{ReaderT} over
  \texttt{StateM} combining read-only access to the environment and root name
  with mutable tracking of visited nodes and accumulated dependencies.

  Defined as $\texttt{ReaderT Context (StateM State)}$.

  \uses{la:collect-used-context, la:collect-used-state} -/)
  (proof := /-- An abbreviation composing \texttt{ReaderT} and \texttt{StateM}. -/)
  (uses := ["la:collect-used-context", "la:collect-used-state"])]
  Architect.CollectUsed.M

attribute [blueprint "la:collect-used-collect"
  (keyDeclaration := true)
  (title := "Collect Dependencies")
  (statement := /-- The core recursive traversal that walks the expression tree of a constant
  to discover blueprint dependencies.

  For each constant $c$ encountered:
  \begin{enumerate}
    \item If $c$ has been visited, return immediately (cycle prevention).
    \item Mark $c$ as visited.
    \item If $c \neq \texttt{root}$ and $c$ has a \texttt{@[blueprint]} annotation,
          record it as a dependency and stop recursing (blueprint nodes are
          treated as opaque boundaries).
    \item Otherwise, pattern-match on the \texttt{ConstantInfo} kind:
          \begin{itemize}
            \item Axioms: record directly as dependencies
            \item Definitions/theorems/opaques: recurse into both type and value
            \item Constructors/recursors: recurse into the type only
            \item Quotient/missing: skip
          \end{itemize}
  \end{enumerate}

  This produces the irreflexive transitive closure of blueprint-annotated
  dependencies reachable from a given constant.

  \uses{la:collect-used-monad, la:node} -/)
  (proof := /-- A \texttt{partial def} using \texttt{getUsedConstants} on each
  \texttt{Expr} and recursively calling \texttt{collect} on each result.
  The \texttt{visited} set in \texttt{State} guarantees termination in
  practice despite the \texttt{partial} annotation. -/)
  (uses := ["la:collect-used-monad", "la:node"])]
  Architect.CollectUsed.collect

attribute [blueprint "la:collect-used"
  (keyDeclaration := true)
  (title := "Collect Used Dependencies")
  (statement := /-- The top-level API for dependency inference. Given a constant name,
  returns two disjoint \texttt{NameSet}s: constants used by the type
  (statement dependencies) and constants used by the value
  (proof dependencies).

  The algorithm runs the \texttt{CollectUsed.collect} traversal in two phases:
  \begin{enumerate}
    \item Collect constants reachable from the type expression
    \item Collect constants reachable from the value expression
    \item Subtract type-used from value-used to make the sets disjoint,
          except that \texttt{sorryAx} may appear in both
  \end{enumerate}

  Statement dependencies become dashed edges in the dependency graph;
  proof dependencies become solid edges. This distinction enables visual
  separation of logical dependencies from implementation dependencies.

  \uses{la:collect-used-collect, la:node} -/)
  (proof := /-- Runs two passes of the \texttt{CollectUsed.M} monad: first over
  \texttt{info.type.getUsedConstants}, then over the full constant.
  Converts accumulated arrays to \texttt{NameSet}s and computes
  $\texttt{valueUsed} \setminus \texttt{typeUsed}$ (preserving \texttt{sorryAx}). -/)
  (uses := ["la:collect-used-collect", "la:node"])]
  Architect.collectUsed

end LeanArchitectBlueprint.Annotations
