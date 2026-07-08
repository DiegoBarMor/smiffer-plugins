#!/usr/bin/env python3
"""
SPOCKER: identify RNA binding pockets from a single PDB structure.

Usage:
    python 1_run_pipeline.py <input.pdb> <output_dir> [--keep-intermediate]

Run 0_prepare_input.sh <PDB_ID> first to fetch and clean a structure from
RCSB (demo_spocker/testdata/input/<PDB_ID>.nucl.pdb is a suitable input).

Output (per run, written to <output_dir>):
    <pdb_id>.Pocket1.mrc, <pdb_id>.Pocket2.mrc, ...   (highest score first)
    <pdb_id>_pockets_summary.txt
"""

import argparse
import sys

from pipeline import run_pipeline


def main():
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("pdb_path", help="Input structure file (.pdb or .cif)")
    parser.add_argument("output_dir", help="Directory to write pocket grids into")
    parser.add_argument("--keep-intermediate", action="store_true",
                         help="Keep generated SMIF field grids under output_dir/intermediate")
    args = parser.parse_args()

    pockets = run_pipeline(args.pdb_path, args.output_dir,
                            keep_intermediate=args.keep_intermediate)
    if not pockets:
        sys.exit("No pockets identified.")


if __name__ == "__main__":
    main()
