"""
Wraps the `volgrids` CLI to generate SMIF grids for one structure.

Field file names produced by volgrids (v0.17.1): apbs, stk (stacking),
hphob (hydrophobic), hphil (hydrophilic, unused downstream), hba/hbd
(H-bond acceptor/donor).
"""

import shutil
import subprocess
from pathlib import Path

from . import config

# volgrids field short-name -> semantic name used throughout this package
FIELD_NAME_MAP = {
    "apbs": "apbs",
    "stk": "stacking",
    "hphob": "hydrophobic",
    "hba": "hba",
    "hbd": "hbd",
}
WHOLE_STRUCTURE_FIELDS = ("apbs", "stk", "hphob", "hba", "hbd")


class FieldGenerationError(RuntimeError):
    pass


def _run(cmd, cwd):
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        raise FieldGenerationError(
            f"Command failed: {' '.join(cmd)}\n{result.stdout}\n{result.stderr}"
        )
    return result


def _config_args(overrides: dict) -> list:
    if not overrides:
        return []
    pairs = " ".join(f"{k}={v}" for k, v in overrides.items())
    return ["-c", pairs]


def prepare_workdir(pdb_path: Path, work_dir: Path) -> Path:
    """Copy the input structure into an isolated working directory, since
    volgrids writes its intermediate/output files next to the input file."""
    work_dir.mkdir(parents=True, exist_ok=True)
    local_path = work_dir / pdb_path.name
    shutil.copy(pdb_path, local_path)
    return local_path


def compute_apbs(local_pdb: Path) -> Path:
    """Precompute the APBS potential once so it can be reused (via -a) by
    both the whole-structure and the non-canonical-residue SMIF runs."""
    _run(["volgrids", "apbs", local_pdb.name, "--mrc"], cwd=local_pdb.parent)
    apbs_cache = local_pdb.parent / f"{local_pdb.name}.mrc"
    if not apbs_cache.exists():
        raise FieldGenerationError(f"APBS cache not produced: {apbs_cache}")
    return apbs_cache


def compute_whole_structure_fields(local_pdb: Path, apbs_cache: Path, out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = ["volgrids", "smiffer", local_pdb.name, "-a", str(apbs_cache), "-o", str(out_dir)]
    cmd += _config_args(config.WHOLE_STRUCTURE_CONFIG)
    _run(cmd, cwd=local_pdb.parent)
    return _collect_field_paths(out_dir, local_pdb.stem, WHOLE_STRUCTURE_FIELDS)


def compute_hbond_subset_fields(local_pdb: Path, residue_selectors: list,
                                 apbs_cache: Path, out_dir: Path) -> dict:
    if not residue_selectors:
        return {}
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        "volgrids", "smiffer", local_pdb.name,
        "-r", *residue_selectors,
        "-a", str(apbs_cache),
        "-o", str(out_dir),
    ]
    cmd += _config_args(config.HBOND_SUBSET_CONFIG)
    _run(cmd, cwd=local_pdb.parent)
    return _collect_field_paths(out_dir, local_pdb.stem, ("apbs", "hba", "hbd"))


def _collect_field_paths(out_dir: Path, stem: str, fields) -> dict:
    paths = {}
    for field in fields:
        candidate = out_dir / f"{stem}.{field}.mrc"
        if candidate.exists():
            paths[FIELD_NAME_MAP[field]] = candidate
    return paths
