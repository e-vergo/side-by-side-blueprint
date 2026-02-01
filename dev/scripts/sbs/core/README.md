# sbs.core - Foundation Layer

Core utilities and data structures shared across the sbs package.

## Contents

- `utils.py` - Logging, path utilities, git helpers, lakefile parsing
- `git_ops.py` - Git status, diff, and sync operations
- `ledger.py` - Build metrics and unified ledger data structures

## Design Principles

1. **No command handlers** - Only reusable utilities and data structures
2. **Minimal dependencies** - Only standard library and typing
3. **Absolute imports** - All internal imports use `from sbs.core.X import Y`

## Usage

```python
from sbs.core import log, Logger, get_sbs_root, ARCHIVE_DIR
from sbs.core import BuildMetrics, UnifiedLedger, get_or_create_unified_ledger
from sbs.core import get_repo_status, sync_repo
```
