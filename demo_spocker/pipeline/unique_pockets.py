"""
Combine every refined candidate pocket (from hotspots.py and
hbond_pockets.py) into the final, non-redundant set of pockets:

  1. merge masks that substantially overlap each other,
  2. trim each merged pocket down to voxels near an RNA heavy atom,
  3. discard pockets that are really just chain-terminus artefacts,
  4. score the survivors by how much of each field's total signal they
     capture, and rank them (Pocket1 = highest score).
"""

import numpy as np
from scipy.spatial import cKDTree

from . import config
from .mrc_io import Grid, indices_to_xyz


def _pairwise_overlap_ok(mask_a, mask_b, threshold):
    size_a, size_b = int(np.count_nonzero(mask_a)), int(np.count_nonzero(mask_b))
    if size_a == 0 or size_b == 0:
        return False
    intersection = int(np.count_nonzero(mask_a & mask_b))
    if intersection == 0:
        return False
    return (intersection / size_a >= threshold) and (intersection / size_b >= threshold)


def _merge_overlapping(candidates: list, threshold: float) -> list:
    """Union-find merge of candidates whose masks bidirectionally overlap by
    at least `threshold`. This is a simpler (transitive-closure) stand-in for
    the original's maximal-clique grouping: a chain A-B-C where only A-B and
    B-C (but not A-C) overlap significantly is merged as one group here,
    rather than kept as two overlapping-but-distinct groups."""
    n = len(candidates)
    parent = list(range(n))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i, j):
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[ri] = rj

    for i in range(n):
        for j in range(i + 1, n):
            if _pairwise_overlap_ok(candidates[i]["mask"], candidates[j]["mask"], threshold):
                union(i, j)

    groups = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)

    merged = []
    for indices in groups.values():
        labels = [candidates[i]["label"] for i in indices]
        mask = candidates[indices[0]]["mask"].copy()
        for i in indices[1:]:
            mask |= candidates[i]["mask"]
        merged.append({"labels": labels, "mask": mask})
    return merged


def _trim_by_rna_distance(mask, grid: Grid, atom_xyz, cutoff_a):
    if atom_xyz is None or len(atom_xyz) == 0 or not np.any(mask):
        return mask
    coords = np.where(mask)
    world = indices_to_xyz(coords, grid)
    dists, _ = cKDTree(atom_xyz).query(world, k=1, workers=-1)
    keep = dists <= cutoff_a
    trimmed = np.zeros_like(mask)
    trimmed[tuple(c[keep] for c in coords)] = True
    return trimmed


def _is_terminal_artifact(mask, grid: Grid, terminal_xyz, cutoff_a, voxel_fraction):
    if terminal_xyz is None or len(terminal_xyz) == 0 or not np.any(mask):
        return False
    world = indices_to_xyz(np.where(mask), grid)
    dists, _ = cKDTree(terminal_xyz).query(world, k=1, workers=-1)
    frac_terminal = float(np.mean(dists <= cutoff_a))
    return frac_terminal > voxel_fraction


def _apbs_near_rna(apbs_grid: Grid, atom_xyz, cutoff_a):
    """Restrict the APBS field to voxels near RNA heavy atoms, so a handful
    of very strong but solvent-exposed voxels don't dominate pocket scoring."""
    if atom_xyz is None or len(atom_xyz) == 0:
        return apbs_grid.data
    nz, ny, nx = apbs_grid.shape
    iz, iy, ix = np.mgrid[0:nz, 0:ny, 0:nx]
    world = np.column_stack([
        apbs_grid.origin[0] + ix.ravel() * apbs_grid.voxel_size[0],
        apbs_grid.origin[1] + iy.ravel() * apbs_grid.voxel_size[1],
        apbs_grid.origin[2] + iz.ravel() * apbs_grid.voxel_size[2],
    ])
    dists, _ = cKDTree(atom_xyz).query(world, k=1, workers=-1)
    keep = (dists <= cutoff_a).reshape(apbs_grid.shape)
    out = np.zeros_like(apbs_grid.data)
    out[keep] = apbs_grid.data[keep]
    return out


def _hydrophobic_nonoverlap(hydrophobic_grid: Grid, stacking_grid: Grid, epsilon=1e-6):
    """Zero out hydrophobic voxels that coincide with a stacking hotspot, so
    the two fields aren't double-counted in scoring."""
    overlap = (np.abs(hydrophobic_grid.data) > epsilon) & (np.abs(stacking_grid.data) > epsilon)
    trimmed = hydrophobic_grid.data.copy()
    trimmed[overlap] = 0.0
    return trimmed


def _field_integral(data, mask=None, absolute=True):
    vals = data[mask] if mask is not None else data
    vals = vals[np.isfinite(vals)]
    if len(vals) == 0:
        return 0.0
    return float(np.sum(np.abs(vals)) if absolute else np.sum(vals))


def _score_pockets(merged_pockets, field_data: dict, atom_xyz):
    stacking = field_data.get("stacking")
    hydrophobic = field_data.get("hydrophobic")
    apbs = field_data.get("apbs")
    hba = field_data.get("hba")
    hbd = field_data.get("hbd")

    hyd_trimmed = _hydrophobic_nonoverlap(hydrophobic, stacking) if (hydrophobic and stacking) else None
    apbs_trimmed = _apbs_near_rna(apbs, atom_xyz, config.APBS_RNA_KEEP_CUTOFF_A) if apbs else None

    totals = {}
    if stacking is not None:
        totals["stacking"] = _field_integral(stacking.data, absolute=False)
    if hyd_trimmed is not None:
        totals["hydrophobic"] = _field_integral(hyd_trimmed, absolute=False)
    stk_hyd_combined = totals.get("stacking", 0.0) + totals.get("hydrophobic", 0.0)
    if apbs_trimmed is not None:
        totals["apbs"] = _field_integral(apbs_trimmed)
    if hba is not None:
        totals["hba"] = _field_integral(hba.data)
    if hbd is not None:
        totals["hbd"] = _field_integral(hbd.data)

    raw_scores = []
    for pocket in merged_pockets:
        mask = pocket["mask"]
        score = 0.0
        if stacking is not None and stk_hyd_combined > 0:
            score += _field_integral(stacking.data, mask, absolute=False) / stk_hyd_combined
        if hyd_trimmed is not None and stk_hyd_combined > 0:
            score += _field_integral(hyd_trimmed, mask, absolute=False) / stk_hyd_combined
        if apbs_trimmed is not None and totals.get("apbs", 0.0) > 0:
            score += _field_integral(apbs_trimmed, mask) / totals["apbs"]
        if hba is not None and totals.get("hba", 0.0) > 0:
            score += _field_integral(hba.data, mask) / totals["hba"]
        if hbd is not None and totals.get("hbd", 0.0) > 0:
            score += _field_integral(hbd.data, mask) / totals["hbd"]
        raw_scores.append(score)

    total = sum(raw_scores)
    return [s / total for s in raw_scores] if total > 0 else [0.0] * len(raw_scores)


def build_unique_pockets(candidates: list, grid: Grid, field_data: dict,
                          atom_xyz, terminal_xyz) -> list:
    """candidates: [{"label": str, "mask": ndarray}], all sharing `grid`.
    Returns ranked pockets: [{"name","labels","mask","score","volume_a3"}]."""
    if not candidates:
        return []

    merged = _merge_overlapping(candidates, config.SIGNIFICANT_OVERLAP_FRACTION)

    survivors = []
    for pocket in merged:
        trimmed = _trim_by_rna_distance(pocket["mask"], grid, atom_xyz, config.RNA_TRIM_CUTOFF_A)
        if not np.any(trimmed):
            continue
        if _is_terminal_artifact(trimmed, grid, terminal_xyz,
                                  config.TERMINAL_ZONE_CUTOFF_A, config.TERMINAL_VOXEL_FRACTION):
            continue
        survivors.append({"labels": pocket["labels"], "mask": trimmed})

    if not survivors:
        return []

    scores = _score_pockets(survivors, field_data, atom_xyz)
    ranked = sorted(zip(scores, survivors), key=lambda t: t[0], reverse=True)

    results = []
    for rank, (score, pocket) in enumerate(ranked, start=1):
        results.append({
            "name": f"Pocket{rank}",
            "labels": pocket["labels"],
            "mask": pocket["mask"],
            "score": float(score),
            "volume_a3": float(np.count_nonzero(pocket["mask"]) * grid.voxel_volume_a3),
        })
    return results
