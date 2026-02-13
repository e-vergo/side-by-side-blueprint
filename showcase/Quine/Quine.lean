import Lean
import Dress

namespace Quine

/-! # A Self-Verifying Quine in Lean 4

This file is simultaneously:
1. A quine (outputs its own source code)
2. A formal proof of its quineness (kernel-verified)
3. Self-referential (the proof is part of the quined output)
4. Runtime-verifiable (the compiled binary can check itself)
-/

-- Section 1: Utilities

open Lean Elab Term in
elab "include_str!" path:str : term => do
  let content ← IO.FS.readFile path.getString
  return mkStrLit content

@[blueprint "find_substr"
  (title := "Substring Finder")
  (statement := /-- Finds the byte offset of a substring within a string.
  Returns the position of the first character of the match. -/)]
def findSubstr (s sub : String) : Option Nat := do
  let parts := s.splitOn sub
  if parts.length ≥ 2 then
    some parts.head!.length
  else
    none

open Lean Elab Term Meta in
elab "quine_formula!" : term => do
  let fileContent ← IO.FS.readFile "Quine.lean"
  let marker := "def d := \""
  let some idx := findSubstr fileContent marker | throwError "marker not found"
  let pfx := (fileContent.take (idx + marker.length - 1)).toString
  let defn ← getConstInfoDefn `Quine.d
  let dVal ← whnf defn.value
  let .lit (.strVal dStr) := dVal | throwError "d is not a string literal"
  return mkStrLit (pfx ++ dStr.quote ++ dStr)

open Lean Elab Term in
elab "file_contains!" path:str ", " sub:str : term => do
  let content ← IO.FS.readFile path.getString
  let needle := sub.getString
  if (content.splitOn needle).length >= 2 then
    return mkConst ``Bool.true []
  else
    return mkConst ``Bool.false []

-- Section 2: The Quine Data

@[blueprint "quine_data"
  (title := "Quine Data String")
  (statement := /-- The data string encodes the suffix of this source file,
  including all proofs and annotations. This is the Kleene payload. -/)
  (uses := ["find_substr"])]
def d := "\n\n-- Section 3: Verification Harness\n\n@[blueprint \"verify_quine\"\n  (title := \"Runtime Verification\")\n  (statement := /-- Executes the quine binary and verifies its output matches the source.\n  Closes the empirical loop: the compiled binary actually outputs itself.\n  \\uses{quine_correct} -/)\n  (uses := [\"quine_correct\"])]\ndef verifyQuine : IO Bool := do\n  let output ← IO.Process.output { cmd := \".lake/build/bin/quine\" }\n  let source ← IO.FS.readFile \"Quine.lean\"\n  return output.stdout == source\n\n-- Section 4: The Quine Executable\n\n@[blueprint \"quine_main\"\n  (title := \"Quine Entry Point\")\n  (statement := /-- Outputs the source code by reconstructing it from embedded data.\n  The prefix is computed at compile time; no files are read at runtime.\n  In verify mode, runs the binary and checks its output. \\uses{quine_data, verify_quine} -/)\n  (uses := [\"quine_data\", \"verify_quine\"])]\ndef _root_.main (args : List String) : IO UInt32 := do\n  if args.contains \"--verify\" then\n    let passed ← Quine.verifyQuine\n    if passed then\n      IO.println \"✓ Quine output matches source\"\n      IO.FS.createDirAll \".lake/build\"\n      IO.FS.writeFile \".lake/build/soundness.json\"\n        \"{\\\"checks\\\":[{\\\"name\\\":\\\"Runtime Verification\\\",\\\"passed\\\":true,\\\"detail\\\":\\\"Executable output matches source file\\\",\\\"url\\\":\\\"verification.html#verify_quine\\\"}]}\"\n      return 0\n    else\n      IO.println \"✗ Quine output does NOT match source\"\n      IO.FS.createDirAll \".lake/build\"\n      IO.FS.writeFile \".lake/build/soundness.json\"\n        \"{\\\"checks\\\":[{\\\"name\\\":\\\"Runtime Verification\\\",\\\"passed\\\":false,\\\"detail\\\":\\\"Output mismatch\\\",\\\"url\\\":\\\"verification.html#verify_quine\\\"}]}\"\n      return 1\n  else\n    let file := include_str! \"Quine.lean\"\n    let marker := \"def d := \\\"\"\n    let pfx := (file.take ((findSubstr file marker).get! + marker.length - 1)).toString\n    IO.print pfx\n    IO.print d.quote\n    IO.print d\n    return 0\n\n-- Section 5: Proofs\n\n@[blueprint \"quine_correct\"\n  (title := \"Quine Correctness\")\n  (keyDeclaration := true)\n  (statement := /-- The quine formula equals the source file.\n  Both sides elaborate to identical string literals at compile time.\n  The kernel verifies definitional equality. \\uses{quine_data} -/)\n  (proof := /-- By definitional equality: \\texttt{rfl}. -/)\n  (uses := [\"quine_data\"])]\ntheorem quine_correct : quine_formula! = include_str! \"Quine.lean\" := rfl\n\n@[blueprint \"self_ref\"\n  (title := \"Self-Reference\")\n  (statement := /-- The quine output contains the text of its own correctness theorem.\n  Verified at elaboration time using compiled string operations,\n  then witnessed by \\texttt{rfl}. Same trust model as \\texttt{include\\_str!}. \\uses{quine_correct} -/)\n  (proof := /-- Elaboration-time check plus \\texttt{rfl}. -/)\n  (uses := [\"quine_correct\"])]\ntheorem self_referential :\n    (file_contains! \"Quine.lean\", \"theorem quine_correct\") = true := rfl\n\n@[blueprint \"annotations_ref\"\n  (title := \"Blueprint Self-Reference\")\n  (statement := /-- The quine output contains its own blueprint annotations.\n  The SBS metadata that generates the dependency graph is itself part\n  of the quined source. \\uses{self_ref} -/)\n  (proof := /-- Elaboration-time check plus \\texttt{rfl}. -/)\n  (uses := [\"self_ref\"])]\ntheorem annotations_self_referential :\n    (file_contains! \"Quine.lean\", \"@[blueprint\") = true := rfl\n\n-- Section 6: Verification Proofs\n\n@[blueprint \"verify_self_ref\"\n  (title := \"Verification Self-Reference\")\n  (statement := /-- The source file contains its own runtime verification code.\n  The verification harness is part of the quined output. \\uses{verify_quine} -/)\n  (proof := /-- Elaboration-time check plus \\texttt{rfl}. -/)\n  (uses := [\"verify_quine\"])]\ntheorem verify_self_referential :\n    (file_contains! \"Quine.lean\", \"def verifyQuine\") = true := rfl\n\n-- Section 7: Post-Elaboration Verification\n\ninitialize do\n  let fileContent ← IO.FS.readFile \"Quine.lean\"\n  let marker := \"def d := \\\"\"\n  let pfx := (fileContent.take ((findSubstr fileContent marker).get! + marker.length - 1)).toString\n  let reconstructed := pfx ++ d.quote ++ d\n  unless reconstructed == fileContent do\n    throw <| IO.userError \"Post-elaboration quine verification failed\"\n\nend Quine\n"

-- Section 3: Verification Harness

@[blueprint "verify_quine"
  (title := "Runtime Verification")
  (statement := /-- Executes the quine binary and verifies its output matches the source.
  Closes the empirical loop: the compiled binary actually outputs itself.
  \uses{quine_correct} -/)
  (uses := ["quine_correct"])]
def verifyQuine : IO Bool := do
  let output ← IO.Process.output { cmd := ".lake/build/bin/quine" }
  let source ← IO.FS.readFile "Quine.lean"
  return output.stdout == source

-- Section 4: The Quine Executable

@[blueprint "quine_main"
  (title := "Quine Entry Point")
  (statement := /-- Outputs the source code by reconstructing it from embedded data.
  The prefix is computed at compile time; no files are read at runtime.
  In verify mode, runs the binary and checks its output. \uses{quine_data, verify_quine} -/)
  (uses := ["quine_data", "verify_quine"])]
def _root_.main (args : List String) : IO UInt32 := do
  if args.contains "--verify" then
    let passed ← Quine.verifyQuine
    if passed then
      IO.println "✓ Quine output matches source"
      IO.FS.createDirAll ".lake/build"
      IO.FS.writeFile ".lake/build/soundness.json"
        "{\"checks\":[{\"name\":\"Runtime Verification\",\"passed\":true,\"detail\":\"Executable output matches source file\",\"url\":\"verification.html#verify_quine\"}]}"
      return 0
    else
      IO.println "✗ Quine output does NOT match source"
      IO.FS.createDirAll ".lake/build"
      IO.FS.writeFile ".lake/build/soundness.json"
        "{\"checks\":[{\"name\":\"Runtime Verification\",\"passed\":false,\"detail\":\"Output mismatch\",\"url\":\"verification.html#verify_quine\"}]}"
      return 1
  else
    let file := include_str! "Quine.lean"
    let marker := "def d := \""
    let pfx := (file.take ((findSubstr file marker).get! + marker.length - 1)).toString
    IO.print pfx
    IO.print d.quote
    IO.print d
    return 0

-- Section 5: Proofs

@[blueprint "quine_correct"
  (title := "Quine Correctness")
  (keyDeclaration := true)
  (statement := /-- The quine formula equals the source file.
  Both sides elaborate to identical string literals at compile time.
  The kernel verifies definitional equality. \uses{quine_data} -/)
  (proof := /-- By definitional equality: \texttt{rfl}. -/)
  (uses := ["quine_data"])]
theorem quine_correct : quine_formula! = include_str! "Quine.lean" := rfl

@[blueprint "self_ref"
  (title := "Self-Reference")
  (statement := /-- The quine output contains the text of its own correctness theorem.
  Verified at elaboration time using compiled string operations,
  then witnessed by \texttt{rfl}. Same trust model as \texttt{include\_str!}. \uses{quine_correct} -/)
  (proof := /-- Elaboration-time check plus \texttt{rfl}. -/)
  (uses := ["quine_correct"])]
theorem self_referential :
    (file_contains! "Quine.lean", "theorem quine_correct") = true := rfl

@[blueprint "annotations_ref"
  (title := "Blueprint Self-Reference")
  (statement := /-- The quine output contains its own blueprint annotations.
  The SBS metadata that generates the dependency graph is itself part
  of the quined source. \uses{self_ref} -/)
  (proof := /-- Elaboration-time check plus \texttt{rfl}. -/)
  (uses := ["self_ref"])]
theorem annotations_self_referential :
    (file_contains! "Quine.lean", "@[blueprint") = true := rfl

-- Section 6: Verification Proofs

@[blueprint "verify_self_ref"
  (title := "Verification Self-Reference")
  (statement := /-- The source file contains its own runtime verification code.
  The verification harness is part of the quined output. \uses{verify_quine} -/)
  (proof := /-- Elaboration-time check plus \texttt{rfl}. -/)
  (uses := ["verify_quine"])]
theorem verify_self_referential :
    (file_contains! "Quine.lean", "def verifyQuine") = true := rfl

-- Section 7: Post-Elaboration Verification

initialize do
  let fileContent ← IO.FS.readFile "Quine.lean"
  let marker := "def d := \""
  let pfx := (fileContent.take ((findSubstr fileContent marker).get! + marker.length - 1)).toString
  let reconstructed := pfx ++ d.quote ++ d
  unless reconstructed == fileContent do
    throw <| IO.userError "Post-elaboration quine verification failed"

end Quine
