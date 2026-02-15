/-
Generate HTML output from the LeanArchitect Blueprint document.
-/
import SBSBlueprint
import LeanArchitectBlueprint.Blueprint

open Verso.Genre.SBSBlueprint.Main

def main : IO UInt32 :=
  sbsBlueprintMain (%doc LeanArchitectBlueprint.Blueprint) (config := {
    outputDir := ".lake/build/verso",
    buildDir := ".lake/build",
    title := "LeanArchitect Blueprint",
    outputFileName := "blueprint_verso",
    verbose := true,
  })
