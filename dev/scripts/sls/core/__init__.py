"""
sls.core - Re-exports from sbs_core shared package.

This module exists for compatibility. All core functionality lives in sbs_core.
Use `from sbs_core.utils import ...` or `from sbs_core.ledger import ...` directly.
"""

# Re-export everything from sbs_core for convenience
try:
    from sbs_core import *  # noqa: F401,F403
except ImportError:
    pass
