import Architect

open Architect

namespace LeanArchitectBlueprint.Annotations

-- ============================================================================
-- === Architect.CrossRef ===
-- ============================================================================

attribute [blueprint "la:signature-components"
  (keyDeclaration := true)
  (title := "Signature Components")
  (statement := /-- Components extracted from a Lean constant's type signature by walking the
  forall telescope. Decomposes a type $\forall (x_1 : T_1) \cdots (x_n : T_n),\; C$ into:
  \begin{itemize}
    \item \texttt{quantifiedVars}: the binder names $x_i$ paired with their types $T_i$
    \item \texttt{hypotheses}: the subset of binders whose names begin with \texttt{h} or \texttt{H},
          following the Lean naming convention for proof terms
    \item \texttt{conclusion}: the body type $C$ remaining after all binders are consumed
    \item \texttt{keyIdentifiers}: constant names from the signature filtered to known algebraic
          structures (e.g.\ \texttt{Group}, \texttt{Ring}, \texttt{TopologicalSpace})
  \end{itemize}

  This decomposition enables heuristic cross-referencing between the formal Lean signature
  and the informal LaTeX statement text. -/)
  (proof := /-- A four-field structure deriving \texttt{Inhabited}. The \texttt{keyIdentifiers}
  field stores only names passing the \texttt{isMathStructure} filter, keeping the set
  small enough for quadratic matching against statement words. -/)]
  SignatureComponents

attribute [blueprint "la:extract-signature-components"
  (keyDeclaration := true)
  (title := "Extract Signature Components")
  (statement := /-- Walk the forall telescope of a Lean type expression and extract
  \texttt{SignatureComponents}.

  The algorithm iterates while \texttt{Expr.isForall} holds, accumulating binders into
  \texttt{quantifiedVars} and classifying those with \texttt{h}/\texttt{H}-prefixed names
  as hypotheses. At each binder, an iterative worklist traversal
  collects all \texttt{Expr.const} names from the binder type. The same collection runs
  on the final conclusion type. The union is filtered to a curated list of 17 algebraic
  and topological structure names to produce \texttt{keyIdentifiers}.

  \uses{la:signature-components} -/)
  (proof := /-- Pure function using \texttt{Id.run} with mutable accumulators. The inner
  \texttt{collectExprConsts} uses an explicit stack (avoiding recursion) with a
  \texttt{NameSet} visited guard to handle DAG-shaped expressions. -/)
  (uses := ["la:signature-components"])]
  extractSignatureComponents

attribute [blueprint "la:statement-components"
  (keyDeclaration := true)
  (title := "Statement Components")
  (statement := /-- Components extracted from a LaTeX statement string by lexical analysis.
  Captures the linguistic structure of the informal mathematical text:
  \begin{itemize}
    \item \texttt{mathIdentifiers}: alphabetic tokens found inside \texttt{\$...\$} math mode
    \item \texttt{quantifierCount}: occurrences of ``for all'', ``for every'', $\forall$, $\exists$
    \item \texttt{hasImplication}: presence of ``implies'', ``then'', \texttt{\textbackslash implies},
          $\to$, $\leftrightarrow$
    \item \texttt{hasConjunction}: presence of ``and'', ``both'', \texttt{\textbackslash land}, $\wedge$
    \item \texttt{hasExistential}: presence of ``exists'', ``there'', \texttt{\textbackslash exists}, $\exists$
    \item \texttt{allWords}: all ASCII-alphanumeric tokens, lowercased
  \end{itemize}

  These features form the basis for heuristic drift detection between LaTeX statements
  and Lean signatures. -/)
  (proof := /-- A six-field structure deriving \texttt{Inhabited}. Fields are boolean or
  count-valued, designed for cheap comparison against \texttt{SignatureComponents}. -/)]
  StatementComponents

attribute [blueprint "la:extract-statement-components"
  (title := "Extract Statement Components")
  (statement := /-- Parse a LaTeX statement string into \texttt{StatementComponents} by:
  \begin{enumerate}
    \item Extracting inline math blocks between unescaped \texttt{\$} delimiters
    \item Tokenizing math blocks into alphabetic identifiers
    \item Splitting the full text into lowercased ASCII words
    \item Counting quantifier phrases (``for all'', ``for every'', $\forall$, $\exists$)
    \item Detecting implication, conjunction, and existential language via both
          English keywords and LaTeX commands
  \end{enumerate}

  The parser correctly handles escaped delimiters (\texttt{\textbackslash\$}) and
  both inline (\texttt{\$...\$}) and display (\texttt{\textbackslash[...\textbackslash]})
  math modes.

  \uses{la:statement-components} -/)
  (proof := /-- Pure function using \texttt{Id.run}. Math extraction uses a state machine
  tracking \texttt{inMath} and \texttt{prevBackslash} flags over the character list. -/)
  (uses := ["la:statement-components"])]
  extractStatementComponents

attribute [blueprint "la:cross-ref-diag"
  (title := "Cross-Reference Diagnostic")
  (statement := /-- A single cross-reference diagnostic containing a warning message.
  Produced by heuristic checks that compare \texttt{SignatureComponents} against
  \texttt{StatementComponents}. Like \texttt{ValidationDiag}, these are advisory only
  and never cause build failures.

  \uses{la:signature-components, la:statement-components} -/)
  (proof := /-- A single-field structure wrapping a \texttt{String}, deriving \texttt{Repr}. -/)
  (uses := ["la:signature-components", "la:statement-components"])]
  CrossRefDiag

attribute [blueprint "la:cross-reference-check"
  (keyDeclaration := true)
  (title := "Cross-Reference Check")
  (statement := /-- The top-level cross-reference analysis entry point. Runs three heuristic
  rules to detect drift between a Lean type signature and its LaTeX statement:

  \begin{enumerate}
    \item \textbf{Math structure match}: if the Lean signature mentions algebraic structures
          (e.g.\ \texttt{Group}, \texttt{Ring}), the statement text should reference them.
          Uses case-insensitive substring matching against both prose words and math-mode
          identifiers.
    \item \textbf{Quantifier balance}: flags when the signature has $\geq 5$ quantified
          variables but the statement contains zero quantifier language. The high threshold
          avoids false positives from implicit binders.
    \item \textbf{Declaration name relevance}: splits the Lean name by underscores,
          filters tokens longer than 3 characters and not in a stop-word list, then checks
          whether \emph{any} token appears in the statement. Only flags when $\geq 2$
          meaningful tokens exist and none match.
  \end{enumerate}

  All rules are conservative: better to miss real drift than to produce false warnings.
  Statements with fewer than 3 words are skipped entirely (likely placeholders).

  \uses{la:signature-components, la:statement-components, la:cross-ref-diag} -/)
  (proof := /-- Sequentially applies \texttt{checkMathStructureMatch},
  \texttt{checkQuantifierBalance}, and \texttt{checkNameRelevance}, collecting
  diagnostics into a single array. -/)
  (uses := ["la:signature-components", "la:statement-components", "la:cross-ref-diag"])]
  crossReferenceCheck

-- ============================================================================
-- === Architect.Validation ===
-- ============================================================================
-- Note: la:validation-diag and la:validate-statement are already annotated
-- in LeanArchitectBlueprint.lean. Only the sub-validators are annotated here.

attribute [blueprint "la:validate-completeness"
  (title := "Validate Statement Completeness")
  (statement := /-- Check that a blueprint statement string is non-empty after trimming
  whitespace. This is the first validation gate: if the statement is empty, downstream
  checks (brace balance, math delimiters) are skipped to avoid vacuous diagnostics.

  \uses{la:validation-diag} -/)
  (proof := /-- Applies \texttt{String.trimAscii} and checks \texttt{isEmpty}. Returns
  \texttt{some ValidationDiag} on failure, \texttt{none} on success. -/)
  (uses := ["la:validation-diag"])]
  validateStatementCompleteness

attribute [blueprint "la:validate-brace-balance"
  (title := "Validate Brace Balance")
  (statement := /-- Verify that LaTeX braces \texttt{\{} and \texttt{\}} are balanced in a
  statement string. Uses a recursive descent over the character list, maintaining an integer
  depth counter. Correctly handles:
  \begin{itemize}
    \item Escaped braces: \texttt{\textbackslash\{} and \texttt{\textbackslash\}} are skipped
    \item Escaped backslashes: \texttt{\textbackslash\textbackslash} followed by a brace
          is treated correctly
  \end{itemize}

  Reports the count of unmatched opening or closing braces. A balance of zero means
  all braces are paired.

  \uses{la:validation-diag} -/)
  (proof := /-- Tail-recursive function \texttt{go} over \texttt{List Char} with an
  \texttt{Int} accumulator. Pattern-matches on two-character sequences for escape handling. -/)
  (uses := ["la:validation-diag"])]
  validateBraceBalance

attribute [blueprint "la:validate-math-delimiters"
  (title := "Validate Math Delimiters")
  (statement := /-- Verify that inline math delimiters (\texttt{\$...\$}) and display math
  delimiters (\texttt{\textbackslash[...\textbackslash]}) are balanced in a statement string.

  For inline math, counts unescaped \texttt{\$} characters and checks for even parity.
  For display math, independently counts \texttt{\textbackslash[} and \texttt{\textbackslash]}
  occurrences and verifies they match.

  Does not validate \texttt{\$\$...\$\$} (rare in blueprint statements). Escaped
  \texttt{\textbackslash\$} delimiters are correctly excluded from the count.

  \uses{la:validation-diag} -/)
  (proof := /-- Uses three \texttt{where}-clause helper functions:
  \texttt{countUnescapedDollars}, \texttt{countDisplayOpen}, and \texttt{countDisplayClose},
  each implemented as structural recursion over \texttt{List Char}. -/)
  (uses := ["la:validation-diag"])]
  validateMathDelimiters

-- ============================================================================
-- === Architect.Output ===
-- ============================================================================

-- --- ToLatex Section ---

attribute [blueprint "la:latex-abbrev"
  (title := "LaTeX Type Abbreviation")
  (statement := /-- Type abbreviation \texttt{Latex := String} establishing the convention
  that LaTeX output is represented as plain strings throughout the output pipeline.
  This is a documentation-level type alias with no runtime overhead. -/)
  (proof := /-- A simple \texttt{abbrev} declaration. -/)]
  Latex

attribute [blueprint "la:latex-input"
  (title := "LaTeX Input Command")
  (statement := /-- Generate a \texttt{\textbackslash input\{path\}} LaTeX command from a
  \texttt{System.FilePath}. Normalizes path separators by replacing backslashes with
  forward slashes via \texttt{file.components}, ensuring correct behavior on Windows
  where file paths use \texttt{\textbackslash} which LaTeX would interpret as control sequences.

  \uses{la:latex-abbrev} -/)
  (proof := /-- String concatenation of \texttt{\textbackslash input\{} with
  \texttt{"/".intercalate file.components}. -/)
  (uses := ["la:latex-abbrev"])]
  Latex.input

attribute [blueprint "la:preprocess-latex"
  (title := "Preprocess LaTeX")
  (statement := /-- Identity preprocessing pass for LaTeX strings. Currently a no-op, serving
  as an extension point for future LaTeX transformations (e.g.\ macro expansion,
  character escaping) applied before output.

  \uses{la:latex-abbrev} -/)
  (proof := /-- Returns the input string unchanged. -/)
  (uses := ["la:latex-abbrev"])]
  preprocessLatex

attribute [blueprint "la:inferred-uses"
  (title := "Inferred Uses")
  (statement := /-- The result of dependency inference for a single \texttt{NodePart}.
  Contains:
  \begin{itemize}
    \item \texttt{uses}: an array of LaTeX label strings referencing other blueprint nodes
          that this part depends on
    \item \texttt{leanOk}: a boolean flag that is \texttt{false} when the dependency set
          contains \texttt{sorryAx}, indicating an incomplete proof
  \end{itemize}

  This structure is the bridge between Lean's \texttt{NameSet}-based dependency tracking
  and the LaTeX label system used by the blueprint output. -/)
  (proof := /-- A two-field structure with no derived instances. -/)]
  InferredUses

attribute [blueprint "la:inferred-uses-empty"
  (title := "Empty Inferred Uses")
  (statement := /-- The identity element for \texttt{InferredUses}: an empty uses array
  with \texttt{leanOk = true}. Used as the default when a node has no proof part.

  \uses{la:inferred-uses} -/)
  (proof := /-- Direct construction with \texttt{\#[]} and \texttt{true}. -/)
  (uses := ["la:inferred-uses"])]
  InferredUses.empty

attribute [blueprint "la:inferred-uses-merge"
  (title := "Merge Inferred Uses")
  (statement := /-- Merge an array of \texttt{InferredUses} by taking the union of all
  \texttt{uses} arrays (via \texttt{flatMap}) and the conjunction of all \texttt{leanOk}
  flags (via \texttt{all}). Used when multiple Lean declarations share the same LaTeX
  label and their dependencies must be combined.

  \uses{la:inferred-uses} -/)
  (proof := /-- \texttt{flatMap} concatenates the uses arrays;
  \texttt{all} short-circuits on the first \texttt{false} leanOk. -/)
  (uses := ["la:inferred-uses"])]
  InferredUses.merge

attribute [blueprint "la:node-part-infer-uses"
  (keyDeclaration := true)
  (title := "Infer Uses for Node Part")
  (statement := /-- Resolve the dependency set of a \texttt{NodePart} into LaTeX labels.

  Given a set of Lean constant names \texttt{used} (from \texttt{collectUsed}), this
  function:
  \begin{enumerate}
    \item Merges \texttt{part.uses} (explicit) with \texttt{used} (inferred from the term)
    \item Removes names in \texttt{part.excludes}
    \item Maps each remaining name to its LaTeX label via \texttt{blueprintExt.find?}
    \item Removes the node's own label (no self-edges)
    \item Adds \texttt{part.usesLabels} (explicit label references)
    \item Removes labels in \texttt{part.excludesLabels}
    \item Sets \texttt{leanOk = false} if \texttt{sorryAx} is in the dependency set
  \end{enumerate}

  \uses{la:node-part, la:inferred-uses} -/)
  (proof := /-- Monadic function requiring \texttt{MonadEnv} and \texttt{MonadError}.
  Uses \texttt{Std.HashSet} for label deduplication. -/)
  (uses := ["la:node-part", "la:inferred-uses"])]
  NodePart.inferUses

attribute [blueprint "la:node-infer-uses"
  (keyDeclaration := true)
  (title := "Infer Uses for Node")
  (statement := /-- Compute the full dependency pair (statement uses, proof uses) for a
  blueprint \texttt{Node}. Delegates to \texttt{collectUsed} for Lean-level dependency
  analysis, then resolves the result through \texttt{NodePart.inferUses}.

  When the node has a proof part, statement and proof dependencies are kept separate
  (enabling dashed vs.\ solid edges in the dependency graph). When there is no proof,
  all dependencies are attributed to the statement.

  \uses{la:node, la:node-part-infer-uses, la:inferred-uses} -/)
  (proof := /-- Calls \texttt{collectUsed node.name} to obtain
  \texttt{(statementUsed, proofUsed)}, then applies \texttt{NodePart.inferUses} to
  each part. For proof-less nodes, the union $\texttt{statementUsed} \cup \texttt{proofUsed}$
  is passed to the statement. -/)
  (uses := ["la:node", "la:node-part-infer-uses", "la:inferred-uses"])]
  Node.inferUses

attribute [blueprint "la:node-part-to-latex"
  (title := "Node Part to LaTeX")
  (statement := /-- Render a \texttt{NodePart} as a complete LaTeX environment block.
  Produces output of the form:
  \begin{verbatim}
  \begin{theorem}[Title]
  \uses{la:dep1,la:dep2}
  \leanok
  Statement text...
  \end{theorem}
  \end{verbatim}

  The \texttt{\textbackslash uses} command is emitted only when dependencies are non-empty.
  The \texttt{\textbackslash leanok} marker is emitted only when all merged parts have
  \texttt{leanOk = true} (no \texttt{sorryAx}). The main text falls back through:
  the part's own text, then the first non-empty text in \texttt{allParts}, then
  \texttt{defaultText}.

  \uses{la:node-part, la:inferred-uses, la:preprocess-latex} -/)
  (proof := /-- Monadic string builder accumulating into a mutable \texttt{out} variable.
  Conditionally appends title, uses, leanok, and body sections. -/)
  (uses := ["la:node-part", "la:inferred-uses", "la:preprocess-latex"])]
  NodePart.toLatex

attribute [blueprint "la:node-with-pos-to-latex"
  (keyDeclaration := true)
  (title := "Node With Position to LaTeX")
  (statement := /-- Convert a positioned blueprint node into its complete LaTeX representation,
  handling multi-declaration merging.

  When multiple Lean declarations share the same LaTeX label (e.g.\ a theorem and its
  corollary), this function:
  \begin{enumerate}
    \item Retrieves all Lean names associated with the label via \texttt{getLeanNamesOfLatexLabel}
    \item Looks up all corresponding \texttt{Node} records
    \item Emits \texttt{\textbackslash label}, \texttt{\textbackslash lean},
          \texttt{\textbackslash notready}, \texttt{\textbackslash discussion},
          \texttt{\textbackslash mathlibok}, and position annotations
    \item Merges inferred uses across all declarations
    \item Renders statement and (optional) proof via \texttt{NodePart.toLatex}
  \end{enumerate}

  Status priority for \texttt{\textbackslash notready}: emitted when any node has
  \texttt{notReady} status unless any node has \texttt{mathlibReady}.

  \uses{la:node-part-to-latex, la:node-infer-uses, la:inferred-uses-merge, la:node-status} -/)
  (proof := /-- Monadic function building auxiliary LaTeX commands as a string prefix,
  then delegating to \texttt{NodePart.toLatex} for the statement and proof blocks.
  Uses \texttt{allM isMathlibOk} to check whether all backing declarations come from
  mathlib or standard libraries. -/)
  (uses := ["la:node-part-to-latex", "la:node-infer-uses", "la:inferred-uses-merge", "la:node-status"])]
  NodeWithPos.toLatex

attribute [blueprint "la:latex-artifact"
  (title := "LaTeX Artifact")
  (statement := /-- An auxiliary output file for a single blueprint node, pairing a
  string \texttt{id} (the LaTeX label, used as the filename stem) with the rendered
  LaTeX \texttt{content}. Artifacts are written to
  \texttt{.lake/build/dressed/\{Module\}/\{label\}.tex}.

  \uses{la:latex-abbrev} -/)
  (proof := /-- A two-field structure: \texttt{id : String} and \texttt{content : Latex}. -/)
  (uses := ["la:latex-abbrev"])]
  LatexArtifact

attribute [blueprint "la:latex-output"
  (keyDeclaration := true)
  (title := "LaTeX Output")
  (statement := /-- The complete LaTeX output for a single module, consisting of:
  \begin{itemize}
    \item A \texttt{header} function that, given the artifacts directory path, produces
          a preamble file defining \texttt{\textbackslash newleannode} and
          \texttt{\textbackslash newleanmodule} macros
    \item An \texttt{artifacts} array of per-node \texttt{LatexArtifact} files
  \end{itemize}

  The header is a function (not a string) because it needs the artifacts directory
  path at write time to generate correct \texttt{\textbackslash input} paths.

  \uses{la:latex-artifact, la:latex-abbrev} -/)
  (proof := /-- A two-field structure. The \texttt{header} field has type
  \texttt{System.FilePath $\to$ Latex}. -/)
  (uses := ["la:latex-artifact", "la:latex-abbrev"])]
  LatexOutput

attribute [blueprint "la:node-to-latex-artifact"
  (title := "Node to LaTeX Artifact")
  (statement := /-- Convert a positioned node to a \texttt{LatexArtifact} by rendering
  its LaTeX content and pairing it with the node's label as the artifact ID.

  \uses{la:latex-artifact, la:node-with-pos-to-latex} -/)
  (proof := /-- Delegates to \texttt{NodeWithPos.toLatex} and wraps the result. -/)
  (uses := ["la:latex-artifact", "la:node-with-pos-to-latex"])]
  NodeWithPos.toLatexArtifact

attribute [blueprint "la:blueprint-content-to-latex"
  (title := "Blueprint Content to LaTeX")
  (statement := /-- Convert a \texttt{BlueprintContent} element to its LaTeX string
  representation. For node content, emits an \texttt{\textbackslash inputleannode\{label\}}
  command. For module docstrings, emits the raw documentation text verbatim.

  \uses{la:latex-abbrev} -/)
  (proof := /-- Pattern match on the two constructors of \texttt{BlueprintContent}. -/)
  (uses := ["la:latex-abbrev"])]
  BlueprintContent.toLatex

attribute [blueprint "la:latex-preamble"
  (title := "LaTeX Preamble")
  (statement := /-- Generate the standard LaTeX preamble that defines the macro infrastructure
  for blueprint documents. Defines four commands using \texttt{\textbackslash makeatletter}:
  \begin{itemize}
    \item \texttt{\textbackslash newleannode\{name\}\{latex\}}: register a node's LaTeX content
          in a global control sequence \texttt{\textbackslash leannode@name}
    \item \texttt{\textbackslash inputleannode\{name\}}: expand the registered content
    \item \texttt{\textbackslash newleanmodule\{module\}\{latex\}}: register a module's content
    \item \texttt{\textbackslash inputleanmodule\{module\}}: expand the registered content
  \end{itemize}

  This preamble is prepended to every module's header file.

  \uses{la:latex-abbrev} -/)
  (proof := /-- A monadic function returning a multi-line string literal containing
  the LaTeX macro definitions. -/)
  (uses := ["la:latex-abbrev"])]
  latexPreamble

attribute [blueprint "la:module-to-latex-output"
  (title := "Module to LaTeX Output")
  (statement := /-- Convert an imported module's blueprint contents to a complete
  \texttt{LatexOutput} (header file + per-node artifact files). Retrieves the module's
  \texttt{BlueprintContent} array from the environment, deduplicates by LaTeX label,
  and renders each node to an artifact.

  \uses{la:latex-output, la:node-to-latex-artifact, la:latex-preamble} -/)
  (proof := /-- Delegates to \texttt{getBlueprintContents} and the private
  \texttt{moduleToLatexOutputAux} helper. Operates in \texttt{CoreM}. -/)
  (uses := ["la:latex-output", "la:node-to-latex-artifact", "la:latex-preamble"])]
  moduleToLatexOutput

attribute [blueprint "la:main-module-to-latex-output"
  (title := "Main Module to LaTeX Output")
  (statement := /-- Convert the current (main) module's blueprint contents to a complete
  \texttt{LatexOutput}. Identical to \texttt{moduleToLatexOutput} but reads from the
  current module's environment entries rather than an imported module's.

  \uses{la:latex-output, la:module-to-latex-output} -/)
  (proof := /-- Delegates to \texttt{getMainModuleBlueprintContents} and the private
  \texttt{moduleToLatexOutputAux} helper. Operates in \texttt{CoreM}. -/)
  (uses := ["la:latex-output"])]
  mainModuleToLatexOutput

-- --- ToJson Section ---

attribute [blueprint "la:node-with-pos-to-json"
  (title := "Node With Position to JSON")
  (statement := /-- Serialize a positioned blueprint node to a \texttt{Json} value containing
  all node fields: \texttt{name}, \texttt{latexLabel}, \texttt{statement}, \texttt{proof},
  \texttt{status}, \texttt{notReady}, \texttt{discussion}, \texttt{title}, \texttt{hasLean},
  \texttt{file}, and \texttt{location}.

  Location is serialized as a nested object with \texttt{module}, \texttt{pos}, and
  \texttt{endPos} fields. This JSON representation is consumed by downstream tools
  (Dress, Runway) for manifest generation. -/)
  (proof := /-- Uses Lean's \texttt{json\%} interpolation syntax for type-safe JSON
  construction. Location is mapped through private \texttt{locationToJson} and
  \texttt{rangeToJson} helpers. -/)]
  NodeWithPos.toJson

attribute [blueprint "la:blueprint-content-to-json"
  (title := "Blueprint Content to JSON")
  (statement := /-- Serialize a \texttt{BlueprintContent} element to JSON. Node content
  is tagged with \texttt{"type": "node"} and includes the full node JSON in \texttt{"data"}.
  Module documentation is tagged with \texttt{"type": "moduleDoc"} and includes the
  documentation string in \texttt{"data"}.

  \uses{la:node-with-pos-to-json} -/)
  (proof := /-- Pattern match emitting tagged JSON objects via \texttt{json\%} syntax. -/)
  (uses := ["la:node-with-pos-to-json"])]
  BlueprintContent.toJson

attribute [blueprint "la:module-to-json"
  (title := "Module to JSON")
  (statement := /-- Convert an imported module's blueprint contents to a JSON array.
  Each element is a serialized \texttt{BlueprintContent} (node or module doc).
  The array preserves declaration order within the module.

  \uses{la:blueprint-content-to-json} -/)
  (proof := /-- Maps \texttt{BlueprintContent.toJson} over the result of
  \texttt{getBlueprintContents} and wraps in \texttt{Json.arr}. -/)
  (uses := ["la:blueprint-content-to-json"])]
  moduleToJson

attribute [blueprint "la:main-module-to-json"
  (title := "Main Module to JSON")
  (statement := /-- Convert the current (main) module's blueprint contents to a JSON array.
  Identical to \texttt{moduleToJson} but reads from the current module's environment.

  \uses{la:blueprint-content-to-json, la:module-to-json} -/)
  (proof := /-- Maps \texttt{BlueprintContent.toJson} over the result of
  \texttt{getMainModuleBlueprintContents} and wraps in \texttt{Json.arr}. -/)
  (uses := ["la:blueprint-content-to-json"])]
  mainModuleToJson

-- --- IO Section ---

attribute [blueprint "la:module-to-rel-path"
  (title := "Module to Relative Path")
  (statement := /-- Compute the relative file path for a module's output file, given a file
  extension. Maps a Lean module name (e.g.\ \texttt{Foo.Bar}) to
  \texttt{module/Foo/Bar.\{ext\}} using Lean's \texttt{modToFilePath}. -/)
  (proof := /-- Delegates to \texttt{modToFilePath "module" module ext}. -/)]
  moduleToRelPath

attribute [blueprint "la:library-to-rel-path"
  (title := "Library to Relative Path")
  (statement := /-- Compute the relative file path for a library's index file, given a file
  extension. Maps a library name to \texttt{library/\{name\}.\{ext\}}. -/)
  (proof := /-- Constructs \texttt{System.mkFilePath ["library", library.toString]}
  and appends the extension. -/)]
  libraryToRelPath

attribute [blueprint "la:output-latex-results"
  (keyDeclaration := true)
  (title := "Output LaTeX Results")
  (statement := /-- Write a module's complete LaTeX output to the filesystem. Creates the
  directory structure and writes:
  \begin{itemize}
    \item The header file at \texttt{basePath/module/\{Module\}.tex}, containing
          \texttt{\textbackslash newleannode} definitions and the module body
    \item Per-node artifact files at
          \texttt{basePath/module/\{Module\}.artifacts/\{label\}.tex}
  \end{itemize}

  Returns the array of artifact file paths (currently discarded by callers).
  Creates parent directories as needed via \texttt{FS.createDirAll}.

  \uses{la:latex-output, la:module-to-rel-path} -/)
  (proof := /-- IO function that writes the header via \texttt{FS.writeFile}, then
  maps over artifacts writing each to its own file. -/)
  (uses := ["la:latex-output", "la:module-to-rel-path"])]
  outputLatexResults

attribute [blueprint "la:output-json-results"
  (title := "Output JSON Results")
  (statement := /-- Write a module's blueprint JSON to the filesystem at
  \texttt{basePath/module/\{Module\}.json}. Creates parent directories as needed.

  \uses{la:module-to-rel-path} -/)
  (proof := /-- IO function using \texttt{FS.writeFile} with \texttt{json.pretty}
  for human-readable formatting. -/)
  (uses := ["la:module-to-rel-path"])]
  outputJsonResults

attribute [blueprint "la:output-library-latex"
  (title := "Output Library LaTeX")
  (statement := /-- Write a library-level index \texttt{.tex} file that
  \texttt{\textbackslash input}s all module header files in the library. Produces a
  single file at \texttt{basePath/library/\{LibraryName\}.tex} containing one
  \texttt{\textbackslash input} command per module, separated by blank lines.

  \uses{la:latex-input, la:module-to-rel-path, la:library-to-rel-path} -/)
  (proof := /-- Maps \texttt{Latex.input} over the module paths and joins with
  double newlines. -/)
  (uses := ["la:latex-input", "la:module-to-rel-path", "la:library-to-rel-path"])]
  outputLibraryLatex

attribute [blueprint "la:output-library-json"
  (title := "Output Library JSON")
  (statement := /-- Write a library-level index \texttt{.json} file containing the paths
  to all module JSON files. Produces a JSON object
  \texttt{\{"modules": ["module/A.json", "module/B.json", ...]\}} at
  \texttt{basePath/library/\{LibraryName\}.json}.

  \uses{la:module-to-rel-path, la:library-to-rel-path} -/)
  (proof := /-- Constructs a JSON object with a single \texttt{"modules"} key containing
  an array of relative path strings, written via \texttt{json.pretty}. -/)
  (uses := ["la:module-to-rel-path", "la:library-to-rel-path"])]
  outputLibraryJson

end LeanArchitectBlueprint.Annotations
