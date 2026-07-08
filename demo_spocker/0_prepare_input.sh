#!/bin/bash
set -euo pipefail

PDB=$1

fdata=demo_spocker/testdata/input
path_pdb_0="$fdata/$PDB.raw.pdb"
path_pdb_1="$fdata/$PDB.fixed.pdb"
path_pdb_2="$fdata/$PDB.nucl.pdb"

mkdir -p "$fdata"

#### PART 0: Download the raw file
if [ ! -f "$path_pdb_0" ]; then
    echo ">>> Downloading PDB file for $PDB"
    curl "https://files.rcsb.org/download/$PDB.pdb" --output "$path_pdb_0"
fi

#### PART 1: Clean the raw file with PDB fixer
#### Careful, pdbfixer keeps aminoacid ligands and even replace their "HETATM" with "ATOM"
if [ ! -f "$path_pdb_1" ]; then
    echo ">>> Fixing $path_pdb_0"
    pdbfixer "$path_pdb_0" --replace-nonstandard --keep-heterogens none --output "$path_pdb_1"
fi

#### PART 2: Remove any non-nucleic residue with molutils (MDAnalysis backend)
#### this step is relevant because newer versions of volgrids consider any
#### nucleic/protein residue in the input file, including aminoacid ligands.
if [ ! -f "$path_pdb_2" ]; then
    echo ">>> Ensuring $path_pdb_1 only contains nucleic residues"
    molutils select "nucleic" "$path_pdb_1" "$path_pdb_2"
fi
