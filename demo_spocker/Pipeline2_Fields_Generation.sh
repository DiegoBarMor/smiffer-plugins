#!/bin/bash
# =============================================================================
# generate_fields_pipeline2.sh
# Generates H-bond fields (HBA, HBD, ELE) for non-canonical residues of a
# single PDB. Uses indices_rna_hb_available_modified.py to detect the
# non-canonical residue indices.
# Usage: ./generate_fields_pipeline2.sh <pdb_dir> <file_name.pdb> <output_dir> <path_to_indices_script>
# =============================================================================
set -uo pipefail

if [[ $# -ne 4 ]]; then
    echo "Usage: $0 <pdb_dir> <file_name.pdb> <output_dir> <path_to_indices_rna_hb_available_modified.py>"
    exit 1
fi

PDB_DIR="$1"
FILE_NAME="$2"
OUT_ROOT="$3"
PY_SCRIPT="$4"

NAME="${FILE_NAME%.*}"
OUT_DIR="$OUT_ROOT/Pipeline2_HBond_Fields_${NAME}"
FAILED_LOG="$OUT_ROOT/failed_pdbs_pipeline2.txt"

mkdir -p "$OUT_DIR"

echo ">>> Pipeline 2 — Processing $NAME ..."

(
    set -e

    ####### TODO: clean pdbs and normalize resids (i.e. resids start always from 1, no negatives)
    ######  pdbfixer "$PDB_DIR/$FILE_NAME" --replace-nonstandard --keep-heterogens none --output OUTPUT_GOES_HERE

    # ------------------------------------------------------------------
    # Step 0: Get non-canonical residue indices via Python script
    # ------------------------------------------------------------------
    echo "    [0/3] Detecting non-canonical residue indices for $NAME"
    csv_out="$OUT_DIR/${NAME}_annotation.csv"
    residues_nobp=$(python "$PY_SCRIPT" "$PDB_DIR/$FILE_NAME" "$csv_out")

    if [[ -z "$residues_nobp" ]]; then
        echo "    [WARNING] No non-canonical indices found for $NAME — skipping volgrids."
        exit 0
    fi

    # ------------------------------------------------------------------
    # All volgrids commands must run from pdb_dir with bare filenames.
    # volgrids writes intermediate files (*.pdb.mrc, *.pdb.dx, *.cmap)
    # next to the PDB in CWD.
    # ------------------------------------------------------------------
    cd "$PDB_DIR"

    echo "ALL" $(molutils list resids "$FILE_NAME")
    echo "residues_nobp" $residues_nobp

    config_hbonds="GRID_FORMAT_OUTPUT=MRC DO_SMIF_APBS=true DO_SMIF_HBA=true DO_SMIF_HBD=true DO_SMIF_HYDROPHILIC=false DO_SMIF_HYDROPHOBIC=false DO_SMIF_STACKING=false HBONDS_ONLY_NUCLEOBASE=true"

    # ------------------------------------------------------------------
    # Step 1: SMIF — H-bond fields for non-canonical residues only
    # ------------------------------------------------------------------
    echo "    [1/2] Running SMIF (H-bond, non-canonical) for $NAME"
    yes Y | volgrids smiffer rna "$FILE_NAME" \
        -r "$residues_nobp" \
        -o "$OUT_DIR" \
        -c "$config_hbonds"

    # ------------------------------------------------------------------
    # Step 2: Clean up intermediate files volgrids wrote into pdb_dir
    # ------------------------------------------------------------------
    echo "    [2/2] Cleaning up intermediate files for $NAME"
    rm -f \
        "${PDB_DIR}/${FILE_NAME}.mrc" \
        "${PDB_DIR}/${FILE_NAME}.dx" \
        "${PDB_DIR}/${NAME}.cmap"

    echo "    Done -> $OUT_DIR"

) || {
    EXIT_CODE=$?
    echo "    [ERROR] Processing FAILED for $NAME (exit code $EXIT_CODE) — skipping."
    echo "$NAME" >> "$FAILED_LOG"

    rm -f \
        "${PDB_DIR}/${FILE_NAME}.mrc" \
        "${PDB_DIR}/${FILE_NAME}.dx" \
        "${PDB_DIR}/${NAME}.cmap"
}

echo "All done. Results saved under: $OUT_DIR"
