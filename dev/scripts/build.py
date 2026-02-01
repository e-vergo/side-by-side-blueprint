#!/usr/bin/env python3
"""Side-by-Side Blueprint Build Orchestrator - Entry Point."""
import sys

# Add the scripts directory to path for sbs package
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from sbs.build import main

if __name__ == "__main__":
    sys.exit(main())
