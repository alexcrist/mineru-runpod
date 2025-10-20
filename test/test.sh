#!/usr/bin/env bash

# Exit on error
set -euo pipefail

# Navigate to test dir
cd "$(dirname "$0")"

# Activate venv
source .venv/bin/activate

# Run test.py
python3 test.py