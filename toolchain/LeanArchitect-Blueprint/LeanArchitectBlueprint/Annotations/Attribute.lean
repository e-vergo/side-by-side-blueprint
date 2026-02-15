import Architect
import Dress

open Architect

namespace LeanArchitectBlueprint.Annotations

-- === Architect.Attribute ===
-- The @[blueprint] attribute definition: annotating the annotation system itself.
-- This is the most self-referential module in the toolchain: the very mechanism
-- that creates blueprint nodes is here described *as* blueprint nodes.

-- ─── Configuration ───

attribute [blueprint "la:config"
  (keyDeclaration := true)
  (title := "Blueprint Configuration")
  (statement := /-- The configuration structure for the \texttt{@[blueprint]} attribute,
  encoding all 24 user-facing options that control how a Lean declaration
  appears in the blueprint.

  The fields fall into five categories:
  \begin{itemize}
    \item \textbf{Content} (5 fields): \texttt{statement}, \texttt{proof},
          \texttt{hasProof}, \texttt{above}, \texttt{below} ---
          LaTeX text for the informal mathematical description and surrounding material.
    \item \textbf{Dependencies} (8 fields): \texttt{uses}, \texttt{excludes},
          \texttt{usesLabels}, \texttt{excludesLabels}, \texttt{proofUses},
          \texttt{proofExcludes}, \texttt{proofUsesLabels}, \texttt{proofExcludesLabels} ---
          manual overrides and exclusions for the dependency graph, split between
          statement-level and proof-level edges.
    \item \textbf{Status} (2 fields): \texttt{status} (a \texttt{NodeStatus} value)
          and \texttt{statusExplicit} (whether the user set it manually vs.\ the default).
    \item \textbf{Presentation} (4 fields): \texttt{title}, \texttt{latexEnv},
          \texttt{latexLabel}, \texttt{discussion} --- control the LaTeX rendering
          and cross-reference labels.
    \item \textbf{Dashboard metadata} (7 fields): \texttt{keyDeclaration},
          \texttt{message}, \texttt{priorityItem}, \texttt{blocked},
          \texttt{potentialIssue}, \texttt{technicalDebt}, \texttt{misc} ---
          project management annotations surfaced in the Runway dashboard.
  \end{itemize}

  Every field has a sensible default (most are \texttt{none}, \texttt{false},
  or empty arrays), so the minimal annotation \texttt{@[blueprint]} requires
  zero configuration. This structure is the intermediate representation
  between the parsed syntax and the final \texttt{Node}.

  \uses{la:node-status} -/)
  (proof := /-- A flat structure with 24 fields, all having default values.
  Derives \texttt{Repr} for debugging output. -/)
  (uses := ["la:node-status"])]
  Architect.Config

-- ─── Configuration Accessor ───

attribute [blueprint "la:config-not-ready"
  (title := "Config Not Ready Check")
  (statement := /-- Backwards-compatibility accessor that checks whether a
  \texttt{Config}'s status equals \texttt{notReady}.

  Provided for callers that predate the six-status model and still
  use a boolean ``is this node ready?'' check.

  \uses{la:config, la:node-status} -/)
  (proof := /-- A one-line accessor: delegates to \texttt{BEq} on \texttt{NodeStatus}. -/)
  (uses := ["la:config", "la:node-status"])]
  Architect.Config.notReady

-- ─── Dependency Parsing ───

attribute [blueprint "la:elab-blueprint-uses"
  (keyDeclaration := true)
  (title := "Elaborate Uses Clause")
  (statement := /-- Parses the \texttt{uses := [...]} and \texttt{proofUses := [...]}
  syntax into four parallel arrays:
  \begin{enumerate}
    \item \textbf{Used names} --- Lean constant names resolved via
          \texttt{tryResolveConst} from identifier syntax.
    \item \textbf{Excluded names} --- identifiers prefixed with \texttt{-}
          (negation syntax for dependency exclusion).
    \item \textbf{Used labels} --- raw LaTeX label strings for cross-project
          or cross-document references.
    \item \textbf{Excluded labels} --- label strings prefixed with \texttt{-}.
  \end{enumerate}

  This four-way split enables fine-grained control: users can specify
  dependencies by Lean name (type-checked) or by LaTeX label (unchecked),
  and can exclude auto-inferred dependencies in either namespace.

  \uses{la:config} -/)
  (proof := /-- Pattern-matches on the \texttt{blueprintUses} syntax category,
  using \texttt{filterMapM} for names (which require \texttt{CoreM} resolution)
  and \texttt{filterMap} for labels (pure string extraction). The negation
  prefix \texttt{-} is detected by matching the \texttt{blueprintSingleUses}
  syntax variant. -/)
  (uses := ["la:config"])]
  Architect.elabBlueprintUses

-- ─── Main Configuration Parser ───

attribute [blueprint "la:elab-blueprint-config"
  (keyDeclaration := true)
  (title := "Elaborate Blueprint Configuration")
  (statement := /-- The central configuration parser for the \texttt{@[blueprint]} attribute.
  Transforms raw Lean syntax into a fully populated \texttt{Config} structure.

  The parser operates in two phases:
  \begin{enumerate}
    \item \textbf{Initialization}: creates a default \texttt{Config} with only
          the \texttt{trace} flag and optional label extracted from the attribute
          syntax header.
    \item \textbf{Option iteration}: walks the array of \texttt{blueprintOption}
          syntax nodes, pattern-matching each against the 22 option variants
          (statement, hasProof, proof, above, below, uses, proofUses, title,
          notReady, ready, mathlibReady, discussion, latexEnv, latexLabel,
          keyDeclaration, message, priorityItem, blocked, potentialIssue,
          technicalDebt, misc, skipValidation, skipCrossRef) and mutating the
          config record accordingly.
  \end{enumerate}

  The parser is purely syntactic: it performs no semantic validation
  (that happens later in the \texttt{initialize} block that registers the
  attribute). Status flags use the ``last writer wins'' convention ---
  if multiple status flags are set, the last one in source order takes effect.

  \uses{la:config, la:elab-blueprint-uses} -/)
  (proof := /-- A large \texttt{match} on the attribute syntax, followed by a
  \texttt{for} loop over option syntax nodes. Each option is handled by a
  nested \texttt{match} with one branch per \texttt{blueprintOption} variant.
  Doc comment text is extracted via \texttt{getDocStringText} with
  \texttt{trimAscii.copy} for clean whitespace handling. -/)
  (uses := ["la:config", "la:elab-blueprint-uses"])]
  Architect.elabBlueprintConfig

-- ─── Node Assembly ───

attribute [blueprint "la:has-proof"
  (title := "Has Proof Predicate")
  (statement := /-- Determines whether a declaration should have a separate proof
  part in the blueprint.

  The decision follows a three-level priority:
  \begin{enumerate}
    \item If the user explicitly set \texttt{hasProof := true/false}, use that.
    \item If a \texttt{proof} text was provided, the node has a proof.
    \item Otherwise, check if the original declaration was a \texttt{theorem}
          (via \texttt{wasOriginallyTheorem} from the Lean environment).
  \end{enumerate}

  This allows definitions to opt into proof parts (useful for constructive
  definitions where the construction is the ``proof'') and theorems to
  opt out (for trivial results where splitting is unnecessary).

  \uses{la:config} -/)
  (proof := /-- Chains \texttt{Option.getD} with a disjunction:
  \texttt{cfg.hasProof.getD (cfg.proof.isSome || wasOriginallyTheorem env name)}. -/)
  (uses := ["la:config"])]
  Architect.hasProof

attribute [blueprint "la:mk-statement-part"
  (title := "Make Statement Part")
  (statement := /-- Constructs the statement \texttt{NodePart} from a \texttt{Config}.

  Extracts the statement text (defaulting to the empty string), the
  statement-level dependency arrays (\texttt{uses}, \texttt{excludes},
  \texttt{usesLabels}, \texttt{excludesLabels}), and determines the
  LaTeX environment: \texttt{theorem} if the node has a proof part,
  \texttt{definition} otherwise. The user may override via \texttt{latexEnv}.

  \uses{la:node-part, la:config} -/)
  (proof := /-- Direct field extraction from \texttt{Config} into a \texttt{NodePart}
  literal, with \texttt{Option.getD} for the text and environment fields. -/)
  (uses := ["la:node-part", "la:config"])]
  Architect.mkStatementPart

attribute [blueprint "la:mk-proof-part"
  (title := "Make Proof Part")
  (statement := /-- Constructs the proof \texttt{NodePart} from a \texttt{Config}.

  Uses the proof-level dependency arrays (\texttt{proofUses},
  \texttt{proofExcludes}, \texttt{proofUsesLabels}, \texttt{proofExcludesLabels})
  and always sets the LaTeX environment to \texttt{proof}.

  \uses{la:node-part, la:config} -/)
  (proof := /-- Direct field extraction from \texttt{Config} into a \texttt{NodePart}
  literal with hard-coded \texttt{latexEnv := "proof"}. -/)
  (uses := ["la:node-part", "la:config"])]
  Architect.mkProofPart

attribute [blueprint "la:mk-node"
  (keyDeclaration := true)
  (title := "Make Node")
  (statement := /-- The core node assembly function: transforms a Lean constant name
  and a parsed \texttt{Config} into a complete \texttt{Node}.

  This is where the annotation system's data model crystallizes. The function:
  \begin{enumerate}
    \item Calls \texttt{hasProof} to determine whether statement and proof
          are separate.
    \item Constructs the statement part via \texttt{mkStatementPart}.
    \item If the node has a proof, constructs the proof part via \texttt{mkProofPart}.
    \item Assembles all 16 fields of \texttt{Node}: identity (\texttt{name},
          \texttt{latexLabel}), content (\texttt{statement}, \texttt{proof},
          \texttt{above}, \texttt{below}), status (\texttt{status},
          \texttt{statusExplicit}), presentation (\texttt{discussion},
          \texttt{title}), and dashboard metadata (\texttt{keyDeclaration},
          \texttt{message}, \texttt{priorityItem}, \texttt{blocked},
          \texttt{potentialIssue}, \texttt{technicalDebt}, \texttt{misc}).
  \end{enumerate}

  The resulting \texttt{Node} is stored in the \texttt{blueprintExt}
  environment extension by the attribute registration handler, making it
  available to downstream tools (Dress, Runway) at build time.

  \uses{la:node, la:config, la:has-proof, la:mk-statement-part, la:mk-proof-part} -/)
  (proof := /-- Branches on \texttt{hasProof}: both paths construct a \texttt{Node}
  literal, but the proof-bearing path includes a call to \texttt{mkProofPart}
  while the proof-free path sets \texttt{proof := none}. The \texttt{latexLabel}
  defaults to the string representation of the Lean name if not explicitly set. -/)
  (uses := ["la:node", "la:config", "la:has-proof", "la:mk-statement-part", "la:mk-proof-part"])]
  Architect.mkNode

end LeanArchitectBlueprint.Annotations

#dressNodes
