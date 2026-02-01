#!/bin/bash
# One-click build, launch, and archive for PrimeNumberTheoremAnd
set -e
cd "$(dirname "$0")/../showcase/PrimeNumberTheoremAnd"
python ../../dev/scripts/build.py --capture "$@"
