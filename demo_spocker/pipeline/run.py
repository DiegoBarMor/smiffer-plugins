"""
End-to-end orchestration: PDB in, ranked pocket grids out.

    Pocket1_Volume.mrc, Pocket2_Volume.mrc, ...   (highest score first)
    <pdb_id>_pockets_summary.txt

Candidate pockets come from two sources, mirroring the two pipelines this
package replaces:
  - hotspots.py:      stacking / hydrophobic / electrostatic field overlaps
                       computed over the whole structure.
  - hbond_pockets.py:  hydrogen-bond sites detected around non-canonically
                       paired residues.
Each candidate is refined to a final volume (refine.py) before
unique_pockets.py merges, filters and scores them together.
"""

import shutil
import tempfile
from pathlib import Path

from . import fields, hotspots, hbond_pockets, refine, unique_pockets
from .mrc_io import load_mrc, save_mrc
from .structure import load_structure
from .isovalues import pick_isovalues
from .residues import non_canonical_residue_selectors


def run_pipeline(pdb_path, out_dir, keep_intermediate: bool = False) -> list:
    pdb_path = Path(pdb_path).resolve()
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    work_dir = Path(tempfile.mkdtemp(prefix="spocker_"))
    try:
        return _run(pdb_path, out_dir, work_dir)
    finally:
        if keep_intermediate:
            dest = out_dir / "intermediate"
            if dest.exists():
                shutil.rmtree(dest)
            shutil.move(str(work_dir), str(dest))
        else:
            shutil.rmtree(work_dir, ignore_errors=True)


def _run(pdb_path: Path, out_dir: Path, work_dir: Path) -> list:
    print(f"[1/6] Preparing structure: {pdb_path.name}")
    local_pdb = fields.prepare_workdir(pdb_path, work_dir)
    structure = load_structure(local_pdb)
    atom_xyz = structure.heavy_rna_xyz
    if len(atom_xyz) == 0:
        raise RuntimeError(f"No RNA heavy atoms parsed from {pdb_path}")

    print("[2/6] Generating whole-structure SMIF fields (apbs, stacking, "
          "hydrophobic, hba, hbd)")
    apbs_cache = fields.compute_apbs(local_pdb)
    whole_paths = fields.compute_whole_structure_fields(
        local_pdb, apbs_cache, work_dir / "fields_whole")
    field_data = {name: load_mrc(path) for name, path in whole_paths.items()}
    if "apbs" not in field_data:
        raise RuntimeError("APBS field was not generated; cannot continue")
    grid = field_data["apbs"]

    print("[3/6] Detecting field hotspots and candidate pockets")
    isovalues = pick_isovalues(field_data)
    hotspot_pockets = hotspots.build_candidate_pockets(field_data, isovalues, atom_xyz)

    candidates = []
    for pocket in hotspot_pockets:
        refined_mask = refine.refine_pocket(pocket["mask"], grid, atom_xyz)
        if refined_mask is not None:
            candidates.append({"label": pocket["pocket_type"], "mask": refined_mask})
    print(f"       {len(candidates)} hotspot pocket(s) survived refinement")

    print("[4/6] Detecting hydrogen-bond pockets around non-canonical residues")
    residue_selectors = non_canonical_residue_selectors(local_pdb, structure)
    if residue_selectors:
        hb_paths = fields.compute_hbond_subset_fields(
            local_pdb, residue_selectors, apbs_cache, work_dir / "fields_hbond")
        hb_field_data = {name: load_mrc(path) for name, path in hb_paths.items()}
        hb_apbs = hb_field_data.get("apbs")
        if hb_apbs is not None and hb_apbs.shape == grid.shape:
            hbond_sites = hbond_pockets.find_hbond_sites(hb_field_data)
            for i, site in enumerate(hbond_sites, start=1):
                refined_mask = refine.refine_pocket(site["mask"], grid, atom_xyz)
                if refined_mask is not None:
                    candidates.append({"label": f"hbond_site_{i}", "mask": refined_mask})
            print(f"       {len(hbond_sites)} hydrogen-bond site(s) detected")
        else:
            print("       [WARN] hbond-subset grid does not match whole-structure "
                  "grid; skipping hydrogen-bond pockets")
    else:
        print("       no non-canonical residues found; skipping")

    if not candidates:
        print("No candidate pockets survived. Nothing to write.")
        return []

    print("[5/6] Merging, trimming and scoring unique pockets")
    final_pockets = unique_pockets.build_unique_pockets(
        candidates, grid, field_data, atom_xyz, structure.terminal_xyz)

    print(f"[6/6] Writing {len(final_pockets)} pocket grid(s) to {out_dir}")
    pdb_id = pdb_path.stem
    summary_lines = [f"Pockets identified for {pdb_id}", ""]
    for pocket in final_pockets:
        out_path = out_dir / f"{pdb_id}.{pocket['name']}.mrc"
        save_mrc(out_path, pocket["mask"].astype("float32"), grid)
        line = (f"{pocket['name']:<10} score={pocket['score']:.4f}  "
                f"volume={pocket['volume_a3']:.1f} A^3  "
                f"from={'+'.join(pocket['labels'])}")
        print(f"       {line}")
        summary_lines.append(line)

    (out_dir / f"{pdb_id}_pockets_summary.txt").write_text("\n".join(summary_lines) + "\n")
    return final_pockets
