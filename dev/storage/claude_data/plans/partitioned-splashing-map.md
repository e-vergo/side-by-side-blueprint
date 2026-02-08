# Replace Jekyll with Plain HTML Landing Page

## Goal

Remove Jekyll and create a plain HTML landing page styled like the PNT project (https://alexkontorovich.github.io/PrimeNumberTheoremAnd/), without PDF link.

---

## Rationale

Jekyll has caused multiple CI failures (gem conflicts, missing dependencies). A plain HTML file:
- Zero Ruby dependencies
- No build step required
- Guaranteed to work
- Same visual result

---

## Changes

### 1. Create `docs/index.html`

Plain HTML with inline CSS mimicking the Cayman theme:
- Header with blue gradient background (`#09203F` to `#537895`)
- Navigation buttons: Blueprint (web), Documentation, GitHub
- Main content with links to resources
- Footer with maintainer info

Content sections:
- Title: "Crystallographic Restriction Theorem"
- Tagline: "Formal verification of the crystallographic restriction theorem in Lean 4"
- Buttons: Blueprint, Documentation, GitHub
- Links list: Zulip, Blueprint, Dependency graph, Docs, GitHub

### 2. Delete Jekyll files

Remove from `docs/`:
- `index.md`
- `_config.yml`
- `Gemfile`

### 3. Update CI workflow

Remove Jekyll build steps, simplify to:
```yaml
- name: Create site directory
  run: |
    mkdir -p _site
    cp docs/index.html _site/
    cp -r .lake/build/doc _site/docs
    cp -r blueprint/web _site/blueprint
```

---

## Files to Modify

| File | Action |
|------|--------|
| `docs/index.html` | Create (new) |
| `docs/index.md` | Delete |
| `docs/_config.yml` | Delete |
| `docs/Gemfile` | Delete |
| `.github/workflows/lean_action_ci.yml` | Simplify (remove Ruby/Jekyll steps) |

---

## Verification

1. Open `docs/index.html` locally in browser to verify styling
2. Push and verify CI completes without Jekyll errors
3. Check deployed site has styled header, working links
