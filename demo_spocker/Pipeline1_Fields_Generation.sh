#!/bin/bash
# =============================================================================
# generate_fields_pipeline1.sh
# Generates full SMIF fields (ELE, STK, HPb, HPhi, HBA, HBD) for a single PDB
# Usage: ./generate_fields_pipeline1.sh <pdb_dir> <file_name.pdb> <output_dir>
# =============================================================================
set -uo pipefail

if [[ $# -ne 3 ]]; then
    echo "Usage: $0 <pdb_dir> <file_name.pdb> <output_dir>"
    exit 1
fi

PDB_DIR="$1"
FILE_NAME="$2"
OUT_ROOT="$3"
ID="${FILE_NAME%.*}"

GRID_DIR="$OUT_ROOT/Pipeline1_Grids_${ID}"
OUT_DIR="$OUT_ROOT/Pipeline1_Analysis_${ID}"

mkdir -p "$GRID_DIR" "$OUT_DIR"

echo "=================================================="
echo "Pipeline 1 — Processing $ID"
echo "Input structure: $PDB_DIR/$FILE_NAME"
echo "=================================================="

(
    set -eo pipefail
    cd "$PDB_DIR"

    # ----------------------------------------------------------------
    # Step 1: APBS electrostatics
    # ----------------------------------------------------------------
    echo "[1/4] Running APBS for $ID"
    yes Y | volgrids apbs "$FILE_NAME" --mrc

    APBS_MRC="${PDB_DIR}/${FILE_NAME}.mrc"
    if [[ ! -f "$APBS_MRC" ]]; then
        echo "ERROR: APBS output not found: $APBS_MRC"
        exit 1
    fi

    # ----------------------------------------------------------------
    # Step 2: SMIF — all fields, whole structure
    # ----------------------------------------------------------------
    echo "[2/4] Running SMIF (all fields) for $ID"
    yes Y | volgrids smiffer rna "$FILE_NAME" -a "${FILE_NAME}.mrc" -o "$GRID_DIR"

    CMAP_FILE="$GRID_DIR/${ID}.cmap"
    if [[ ! -f "$CMAP_FILE" ]]; then
        echo "ERROR: Expected CMAP file not found: $CMAP_FILE"
        ls -la "$GRID_DIR/" || true
        exit 1
    fi

    # ----------------------------------------------------------------
    # Step 3: Unpack combined CMAP into per-field CMAPs
    # ----------------------------------------------------------------
    echo "[3/4] Unpacking CMAP for $ID"
    yes Y | volgrids vgtools unpack "$CMAP_FILE"

    # ----------------------------------------------------------------
    # Step 4: Convert each unpacked field CMAP -> MRC
    # ----------------------------------------------------------------
    echo "[4/4] Converting CMAP to MRC for $ID"
    FOUND_GRID=0
    for f in "$GRID_DIR"/${ID}.*.cmap; do
        [[ -e "$f" ]] || continue
        FOUND_GRID=1
        OUT_MRC="$OUT_DIR/$(basename "${f%.cmap}.mrc")"
        echo "  Converting: $(basename "$f") -> $(basename "$OUT_MRC")"
        yes Y | volgrids vgtools convert "$f" -m "$OUT_MRC"
    done

    if [[ "$FOUND_GRID" -eq 0 ]]; then
        echo "ERROR: No unpacked CMAP grid files found in $GRID_DIR"
        exit 1
    fi

    MRC_COUNT="$(find "$OUT_DIR" -maxdepth 1 -name "*.mrc" | wc -l)"
    if [[ "$MRC_COUNT" -eq 0 ]]; then
        echo "ERROR: convert ran but no .mrc files found in $OUT_DIR"
        exit 1
    fi

    # Cleanup intermediates written next to the PDB
    rm -f "${PDB_DIR}/${FILE_NAME}.mrc" "${PDB_DIR}/${FILE_NAME}.dx" "${PDB_DIR}/${ID}.cmap"

    echo "Finished $ID — $MRC_COUNT .mrc file(s) saved in: $OUT_DIR"

) && echo "Pipeline 1 SUCCESS: $ID" || echo "Pipeline 1 FAILED: $ID"
