#!/bin/bash
set -euo pipefail

PDB=$1

dir_input=demo_spocker/testdata/input
path_pdb_0="$dir_input/$PDB.raw.pdb"
path_pdb_1="$dir_input/$PDB.fixed.pdb"
path_pdb_2="$dir_input/$PDB.nucl.pdb"

mkdir -p "$dir_input"

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

### [WIP] keeping this intermediary files for now, but the only file needed is this last one
cp "$path_pdb_2" "$dir_input/$PDB.pdb"
