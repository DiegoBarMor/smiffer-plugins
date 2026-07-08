#!/bin/bash
# Run the original legacy/ scripts on a single PDB, for comparing their
# output against pipeline/ (driven by 1_run_pipeline.py).
#
# The legacy scripts are otherwise untouched, but their hardcoded BASE /
# PDB_BASE / HBOND_BASE constants now point at demo_spocker/testdata/legacy_work/
# (see legacy/README.md) instead of the original, dead absolute path. Field
# generation is adapted to the current volgrids CLI (see
# _legacy_prepare_inputs.py and legacy/README.md for why).
#
# Usage: bash run_pipeline_legacy.sh <input.pdb> <output_dir> [--keep-intermediate]
set -euo pipefail

if [[ $# -lt 2 ]]; then
    echo "Usage: $0 <input.pdb> <output_dir> [--keep-intermediate]"
    exit 1
fi

PDB_PATH=$(realpath "$1")
OUT_DIR=$(realpath -m "$2")
KEEP_INTERMEDIATE=0
[[ "${3:-}" == "--keep-intermediate" ]] && KEEP_INTERMEDIATE=1

PDB_ID=$(basename "$PDB_PATH")
PDB_ID=${PDB_ID%.*}

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
LEGACY_DIR="$SCRIPT_DIR/legacy"
WORK="$SCRIPT_DIR/testdata/legacy_work"

echo ">>> [1/3] Preparing legacy input layout + fields for $PDB_ID -> $WORK"
python3 "$SCRIPT_DIR/_legacy_prepare_inputs.py" "$PDB_PATH" "$WORK"

run_step() {
    echo ">>> Running $1"
    python3 "$LEGACY_DIR/$1"
}

echo ">>> [2/3] Running the legacy pipeline stages"
run_step Script1_Pipeline1_Slope_Derived_Fixed_Iso_Values_for_Hotspot.py
run_step Script2_Pipeline1_Detection_of_Binding_Site_Hotspots.py
run_step Script3_Pipeline1_Making_Pocket_Volume_Using_Hotspots.py
python3 "$LEGACY_DIR/Script6_Trimming_APBS_for_Scoring_Unique_Pockets.py" --pdb "$PDB_ID"
python3 "$LEGACY_DIR/Script7_Trimming_Hydrophobic_for_Scoring_Unique_Pockets.py" --pdb "$PDB_ID"

if [[ -f "$WORK/HBond_Fields_Nonstandard_Bases/$PDB_ID/$PDB_ID.apbs.mrc" ]]; then
    run_step Script4_Pipeline2_Hydrogen_Bond_Pocket_Hotspots_Using_HBA_HBD_ELE_Fields.py
    run_step Script5_Pipeline2_Making_Hydrogen_Bond_Pocket_Volume.py
else
    echo ">>> No non-canonical residues / HBond fields; skipping Script4/5"
fi
run_step Script8_Making_Unique_Pockets_Using_All_Previous_Pockets.py

echo ">>> [3/3] Collecting results"
RESULT_DIR="$WORK/Analysis_all_RNAs/$PDB_ID/unique_pockets"
mkdir -p "$OUT_DIR"
if [[ -d "$RESULT_DIR" ]]; then
    cp -v "$RESULT_DIR"/* "$OUT_DIR/"
    echo ">>> Legacy pocket grids written to $OUT_DIR"
    echo ">>> Compare against 1_run_pipeline.py's output for the same PDB"
else
    echo "!!! Legacy pipeline produced no unique_pockets directory for $PDB_ID"
    exit 1
fi

if [[ "$KEEP_INTERMEDIATE" -eq 0 ]]; then
    rm -rf "$WORK"
fi
