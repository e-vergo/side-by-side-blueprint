# sbs.build

Build orchestration package for Side-by-Side Blueprint.

## Module Structure

| Module | Purpose |
|--------|---------|
| `config.py` | Constants, dataclasses (Repo, BuildConfig), project detection |
| `caching.py` | Build artifact caching (~/.sbs-cache/) |
| `compliance.py` | Mathlib version, internal deps validation |
| `phases.py` | Build phases (clean, lake build, lake update, mathlib cache) |
| `orchestrator.py` | BuildOrchestrator class and CLI |
| `inspect.py` | Build inspection and validation commands |
| `versions.py` | Dependency version checking |

## Usage

### As a module

```python
from sbs.build import BuildConfig, BuildOrchestrator

config = BuildConfig(
    project_root=Path("/path/to/project"),
    project_name="MyProject",
    module_name="MyProject",
)

orchestrator = BuildOrchestrator(config)
orchestrator.run()
```

### As CLI entry point

```python
from sbs.build import main
sys.exit(main())
```

Or directly:

```bash
python dev/scripts/build.py --help
python dev/scripts/build.py --dry-run
```

## Design Notes

- **No duplicate code**: Uses `sbs.core.utils` for logging, constants, git utilities
- **Uses `sbs.core.git_ops`** for git sync operations
- **Build phases are standalone functions** in `phases.py`, called by `BuildOrchestrator`
- **Timing metrics** are collected and saved to the unified ledger via `sbs.core.ledger`
