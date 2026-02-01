#!/bin/bash
# One-click build, launch, and archive for General_Crystallographic_Restriction
set -e
cd "$(dirname "$0")/../showcase/General_Crystallographic_Restriction"
python ../../dev/scripts/build.py --capture "$@"
