import Architect
import Dress
import LeanArchitectBlueprint.Annotations.Attribute
import LeanArchitectBlueprint.Annotations.BasicContentCommand
import LeanArchitectBlueprint.Annotations.CrossRefValidationOutput
import LeanArchitectBlueprint.Annotations.RPCTacticLoadCollect

open Architect

-- Retroactive @[blueprint] annotations for LeanArchitect declarations.
-- All annotations are applied from this wrapper project to avoid same-package
-- IR interpreter crashes (Lean 4 limitation with afterCompilation attributes).

-- === Core Types (Basic.lean) ===

attribute [blueprint "la:node-status"
  (keyDeclaration := true)
  (title := "Node Status")
  (statement := /-- The six-level status model for blueprint nodes, determining their
  visual representation in the dependency graph and dashboard.

  The hierarchy reflects formalization progress:
  \texttt{notReady} (default) $\to$ \texttt{ready} $\to$ \texttt{sorry} $\to$
  \texttt{proven} $\to$ \texttt{fullyProven} (auto-computed) $\to$ \texttt{mathlibReady}.

  Three statuses are manually assignable (\texttt{notReady}, \texttt{ready}, \texttt{mathlibReady}),
  two are auto-detected from the proof term (\texttt{sorry}, \texttt{proven}),
  and one is computed by graph traversal (\texttt{fullyProven}). -/)
  (proof := /-- A six-constructor inductive type with \texttt{Inhabited}, \texttt{ToJson},
  \texttt{FromJson}, and \texttt{ToExpr} instances for serialization and metaprogramming. -/)]
  NodeStatus

attribute [blueprint "la:node-part"
  (keyDeclaration := true)
  (title := "Node Part")
  (statement := /-- A component of a blueprint node representing either the statement or proof.

  Each \texttt{NodePart} carries:
  \begin{itemize}
    \item \texttt{text}: LaTeX source for the mathematical content
    \item \texttt{uses}: array of Lean constant names this part depends on
    \item \texttt{usesLabels}: array of LaTeX label strings for cross-references
    \item \texttt{latexEnv}: the LaTeX environment type (e.g., ``theorem'', ``definition'', ``proof'')
  \end{itemize}

  \uses{la:node-status} -/)
  (proof := /-- A four-field structure with \texttt{ToExpr} derivation for metaprogramming. -/)]
  NodePart

attribute [blueprint "la:node"
  (keyDeclaration := true)
  (title := "Node")
  (statement := /-- The central data structure of LeanArchitect: a fully annotated blueprint node
  representing a single Lean declaration with its informal mathematical description.

  A \texttt{Node} aggregates:
  \begin{itemize}
    \item \texttt{name}: the Lean constant name
    \item \texttt{latexLabel}: unique LaTeX cross-reference label
    \item \texttt{statement}: the informal statement (\texttt{NodePart})
    \item \texttt{proof}: optional informal proof (\texttt{NodePart})
    \item \texttt{status}: formalization status (\texttt{NodeStatus})
    \item Dashboard metadata: \texttt{title}, \texttt{keyDeclaration}, \texttt{message},
          \texttt{blocked}, \texttt{potentialIssue}, \texttt{technicalDebt}
  \end{itemize}

  Nodes are stored in the \texttt{blueprintExt} environment extension and
  consumed by Dress for artifact generation.

  \uses{la:node-part, la:node-status} -/)
  (proof := /-- A structure with 16 fields covering identity, content, status, and
  dashboard metadata. Derives \texttt{ToExpr} for compile-time manipulation. -/)
  (uses := ["la:node-part", "la:node-status"])]
  Node

attribute [blueprint "la:validation-diag"
  (title := "Validation Diagnostic")
  (statement := /-- A single validation diagnostic containing a warning message string.
  Validation diagnostics are advisory: they never cause compilation errors,
  only warnings. This ensures that blueprint annotations never break builds. -/)
  (proof := /-- A single-field structure wrapping a \texttt{String}. -/)]
  ValidationDiag

attribute [blueprint "la:validate-statement"
  (keyDeclaration := true)
  (title := "Validate Statement")
  (statement := /-- The top-level validation entry point that runs all LaTeX checks on a
  statement string. Composes completeness checking, brace balance validation,
  and math delimiter verification into a single diagnostic pass.

  Returns an empty array if all checks pass. Short-circuits on empty
  statements to avoid vacuously noisy downstream checks.

  \uses{la:validation-diag} -/)
  (proof := /-- Sequentially applies \texttt{validateStatementCompleteness},
  \texttt{validateBraceBalance}, and \texttt{validateMathDelimiters},
  collecting all diagnostics. -/)
  (uses := ["la:validation-diag"])]
  validateStatement

#dressNodes
