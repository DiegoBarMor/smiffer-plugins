#!/usr/bin/env python3
"""
Prepare the directory layout and input fields that the original legacy/
scripts expect (BASE/PDB_BASE/HBOND_BASE-style folders), so they can be run
on a single PDB for comparison against pipeline/.

The legacy Pipeline1/2 shell scripts call `volgrids smiffer rna ...`, which
no longer exists in the current volgrids CLI (see legacy/README.md), so
field generation here reuses pipeline.fields instead. Only field generation
is reused -- the actual hotspot/pocket-detection/scoring algorithms invoked
afterwards are the original, untouched legacy/Script*.py.

Usage: python _legacy_prepare_inputs.py <input.pdb> <work_dir>
"""

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pipeline import fields, residues, structure

# semantic field name (pipeline/fields.py) -> legacy file suffix (legacy/Script*.py)
LEGACY_FIELD_NAME = {
    "apbs": "apbs",
    "stacking": "stacking",
    "hydrophobic": "hydrophobic",
    "hba": "hbacceptors",
    "hbd": "hbdonors",
}


def _place(semantic_paths: dict, dest_dir: Path, pdb_id: str):
    dest_dir.mkdir(parents=True, exist_ok=True)
    for name, path in semantic_paths.items():
        shutil.copy(path, dest_dir / f"{pdb_id}.{LEGACY_FIELD_NAME[name]}.mrc")


def main():
    pdb_path = Path(sys.argv[1]).resolve()
    work_dir = Path(sys.argv[2]).resolve()
    pdb_id = pdb_path.stem

    pdb_dir = work_dir / "PDBs"
    analysis_dir = work_dir / "Analysis_all_RNAs" / pdb_id
    pdb_dir.mkdir(parents=True, exist_ok=True)
    analysis_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(pdb_path, pdb_dir / f"{pdb_id}.pdb")

    field_work = work_dir / "_field_generation"
    local_pdb = fields.prepare_workdir(pdb_path, field_work)
    apbs_cache = fields.compute_apbs(local_pdb)

    print(f"[legacy-prep] generating whole-structure fields for {pdb_id}")
    whole_paths = fields.compute_whole_structure_fields(local_pdb, apbs_cache, field_work / "whole")
    _place(whole_paths, analysis_dir, pdb_id)

    struct = structure.load_structure(local_pdb)
    selectors = residues.non_canonical_residue_selectors(local_pdb, struct)
    if selectors:
        print(f"[legacy-prep] generating hydrogen-bond fields for "
              f"{len(selectors)} non-canonical residue(s)")
        hbond_dir = work_dir / "HBond_Fields_Nonstandard_Bases" / pdb_id
        hb_paths = fields.compute_hbond_subset_fields(local_pdb, selectors, apbs_cache, field_work / "hbond")
        _place(hb_paths, hbond_dir, pdb_id)
    else:
        print("[legacy-prep] no non-canonical residues found; HBond fields skipped")


if __name__ == "__main__":
    main()
