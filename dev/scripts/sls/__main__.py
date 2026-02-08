"""
Entry point for running sls as a module: python -m sls
"""

import sys
from .cli import main

if __name__ == "__main__":
    sys.exit(main())
