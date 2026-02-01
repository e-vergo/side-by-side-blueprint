# dev/scripts - SBS Development Tooling

Python CLI tooling for Side-by-Side Blueprint development.

## Quick Start

```bash
cd /Users/eric/GitHub/Side-By-Side-Blueprint/dev/scripts

# Activate virtual environment
source .venv/bin/activate

# Run CLI
python -m sbs --help
python -m sbs capture --help
python -m sbs archive --help
```

## Package Structure

```
sbs/
├── core/           # Foundation layer (utils, git, ledger)
├── archive/        # Archive system (entries, iCloud sync, tagging)
├── build/          # Build orchestration (14-phase build)
└── tests/          # All testing infrastructure
    ├── compliance/ # Visual compliance validation
    ├── validators/ # Validator implementations
    ├── rubrics/    # Quality rubrics
    └── pytest/     # Pytest test suite
```

## Key Commands

| Command | Purpose |
|---------|---------|
| `sbs capture` | Capture screenshots from running site |
| `sbs compliance` | Run visual compliance validation |
| `sbs archive upload` | Upload session data to archive |
| `sbs rubric list` | List quality rubrics |
| `sbs status` | Git status across all repos |
| `sbs sync` | Commit and push all repos |

## Build Script

The main build entry point:

```bash
python build.py --help
python build.py --dry-run
```

See [sbs/build/README.md](sbs/build/README.md) for build details.

## Running Tests

```bash
# Full test suite
python -m pytest sbs/tests/pytest -v

# Specific test file
python -m pytest sbs/tests/pytest/test_cli.py -v
```

## Design Principles

- **Absolute imports** throughout (`from sbs.core.utils import ...`)
- **No circular dependencies** - core/ is foundation, others depend on it
- **Single command, single purpose** - each command does one thing well
