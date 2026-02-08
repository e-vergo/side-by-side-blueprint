"""
sbs_core compatibility shim.

Re-exports from sbs.core until the real sbs-core shared package is created.
This allows sls imports like `from sbs_core.utils import log` to work
by proxying to the existing `sbs.core` package.
"""

from sbs.core import *  # noqa: F401,F403
