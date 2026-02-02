#!/bin/bash
# One-click build, launch, and archive for SBS-Test
set -e
cd "$(dirname "$0")/../toolchain/SBS-Test"
python3 ../../dev/scripts/build.py --capture "$@"
