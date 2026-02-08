# Plan: Add fallback to identKind function in SubVerso

## Summary
Modify the `identKind` function in `/Users/eric/GitHub/subverso/src/SubVerso/Highlighting/Code.lean` to add a fallback search using `infoIncludingSyntax` when the exact syntax match returns `.unknown`.

## Location
- File: `/Users/eric/GitHub/subverso/src/SubVerso/Highlighting/Code.lean`
- Lines: 399-409

## Verification
- `infoIncludingSyntax` exists at line 101 in the same file
- It is already used elsewhere in the codebase (lines 1197, 1211, 1405)

## Change

Replace:
```lean
def identKind [Monad m] [MonadLiftT IO m] [MonadFileMap m] [MonadEnv m] [MonadMCtx m] [Alternative m]
    (trees : Array InfoTree) (stx : TSyntax `ident)
    (allowUnknownTyped : Bool := false) :
    ReaderT Context m Token.Kind := do
  let mut kind : Token.Kind := .unknown
  for t in trees do
    for (ci, info) in infoForSyntax t stx do
      if let some seen ← infoKind ci info (allowUnknownTyped := allowUnknownTyped) then
        if seen.priority > kind.priority then kind := seen
      else continue
  pure kind
```

With:
```lean
def identKind [Monad m] [MonadLiftT IO m] [MonadFileMap m] [MonadEnv m] [MonadMCtx m] [Alternative m]
    (trees : Array InfoTree) (stx : TSyntax `ident)
    (allowUnknownTyped : Bool := false) :
    ReaderT Context m Token.Kind := do
  let mut kind : Token.Kind := .unknown
  -- First try exact syntax match
  for t in trees do
    for (ci, info) in infoForSyntax t stx do
      if let some seen ← infoKind ci info (allowUnknownTyped := allowUnknownTyped) then
        if seen.priority > kind.priority then kind := seen
      else continue
  -- If no info found, try broader search for enclosing info nodes
  -- This helps find TermInfo for identifiers inside tactic arguments
  if kind == .unknown then
    for t in trees do
      for (ci, info) in infoIncludingSyntax t stx do
        if let some seen ← infoKind ci info (allowUnknownTyped := allowUnknownTyped) then
          if seen.priority > kind.priority then kind := seen
        else continue
  pure kind
```

## Post-edit verification
```bash
cd /Users/eric/GitHub/subverso && lake build
```

## Status
Ready to execute when Plan mode is disabled.
