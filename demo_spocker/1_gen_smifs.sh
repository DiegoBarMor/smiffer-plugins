#!/bin/bash
set -euo pipefail
# =============================================================================
# Generates full SMIF fields (ELE, STK, HPb, HPhi, HBA, HBD) for a single PDB
# =============================================================================

PDB=$1

dir_input=demo_spocker/testdata/input
dir_smifs=demo_spocker/testdata/smifs
path_pdb_in="$dir_input/$PDB.pdb"

mkdir -p "$dir_smifs"

echo "=================================================="
echo "Pipeline 1 - Processing $PDB"
echo "Input structure: $path_pdb_in"
echo "=================================================="

volgrids smiffer "$path_pdb_in" -o "$dir_smifs" \
    -c OUT_FORMAT=MRC SMIF_STK=true SMIF_HBA=true SMIF_HBD=true \
        SMIF_APBS=true SMIF_HPHOB=true SMIF_HPHIL=false

echo "Pipeline 1 SUCCESS: $PDB"
