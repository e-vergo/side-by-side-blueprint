"""
Entry point for running sbs as a module: python -m sbs
"""

import sys
from .cli import main

if __name__ == "__main__":
    sys.exit(main())
