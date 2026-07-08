#!/bin/bash
set -euo pipefail

if [ ! -f demo_spocker/run.sh ]; then
    echo "Must run this script from the root directory of the repo. Aborting."
    exit 1
fi

PDB=1AJU # [WIP] hardcoded example to match testdata's expected output

bash demo_spocker/0_prepare_input.sh $PDB
