"""
Threshold the whole-structure SMIF fields at their chosen isovalues, find
connected components ("hotspots") in each field, and combine them into
candidate pockets:

  - mixed_fields:           stacking + hydrophobic + apbs, triple overlap
  - stacking_electrostatic: stacking + apbs, overlapping or close together
  - stacking_hydrophobic:   stacking + hydrophobic, overlapping or close
  - electrostatic:          union of all apbs hotspots

Each candidate keeps its component masks, a real_buriedness estimate (how
enclosed it is by RNA heavy atoms) and a pocket_score used to rank pockets
of different types against each other later in unique_pockets.py.
"""

import numpy as np
from scipy import ndimage
from scipy.spatial import cKDTree

from . import config
from .mrc_io import Grid, indices_to_xyz


def threshold_mask(data, iso, field):
    if field == "apbs":
        return np.isfinite(data) & (data <= iso)
    return np.isfinite(data) & (data >= iso)


def connected_components(mask):
    structure = ndimage.generate_binary_structure(3, 2)
    return ndimage.label(mask, structure=structure)


def _estimate_real_buriedness(component_xyz, atom_xyz):
    if len(component_xyz) == 0 or len(atom_xyz) == 0:
        return 0.0
    tree = cKDTree(atom_xyz)
    dists, _ = tree.query(component_xyz, k=1, workers=-1)
    close_frac = float(np.mean(dists <= config.REAL_BURIEDNESS_RADIUS_A))
    far_frac = float(np.mean(dists >= config.ACCESSIBLE_POINT_FAR_A))
    centroid = component_xyz.mean(axis=0)
    local_density = min(1.0, len(tree.query_ball_point(
        centroid, config.REAL_BURIEDNESS_NEIGHBOR_RADIUS_A)) / 80.0)
    centroid_enclosure = min(1.0, len(tree.query_ball_point(
        centroid, config.CENTROID_ENCLOSURE_RADIUS_A)) / 120.0)
    buriedness = (
        0.35 * close_frac + 0.25 * (1.0 - far_frac) +
        0.20 * local_density + 0.20 * centroid_enclosure
    )
    return float(np.clip(buriedness, 0.0, 1.0))


def component_stats(labels, nlab, data, grid: Grid, atom_xyz, field_name):
    comps = []
    for lab in range(1, nlab + 1):
        idx = np.where(labels == lab)
        nvox = len(idx[0])
        if nvox < config.MIN_COMPONENT_VOXELS:
            continue
        vals = data[idx]
        vals_score = np.abs(vals) if field_name == "apbs" else vals
        total = float(np.sum(vals_score))
        comp_xyz = indices_to_xyz(idx, grid)
        comps.append({
            "field": field_name, "indices": idx,
            "nvox": nvox, "sum": total, "density": total / nvox,
            "real_buriedness": _estimate_real_buriedness(comp_xyz, atom_xyz),
        })
    return comps


def _component_mask(shape, idx):
    m = np.zeros(shape, dtype=bool)
    m[idx] = True
    return m


def _union_mask(shape, comps):
    out = np.zeros(shape, dtype=bool)
    for comp in comps:
        out[comp["indices"]] = True
    return out


def _overlap_voxels(shape, idx_a, idx_b):
    ov = _component_mask(shape, idx_a) & _component_mask(shape, idx_b)
    return int(np.count_nonzero(ov)), ov


def _min_distance(idx_a, idx_b, voxel_size_xyz):
    a = np.column_stack(idx_a).astype(float)[:, ::-1] * voxel_size_xyz
    b = np.column_stack(idx_b).astype(float)[:, ::-1] * voxel_size_xyz
    if len(a) == 0 or len(b) == 0:
        return np.inf
    best = np.inf
    for i in range(0, len(a), 1500):
        d2 = ((a[i:i + 1500, None, :] - b[None, :, :]) ** 2).sum(axis=2)
        best = min(best, float(np.min(d2)))
    return float(np.sqrt(best))


def _distance_bonus(dist):
    if dist > config.CLOSE_DISTANCE_A:
        return None
    if dist <= config.VERY_CLOSE_DISTANCE_A:
        return 1.0
    span = config.CLOSE_DISTANCE_A - config.VERY_CLOSE_DISTANCE_A
    return max(0.0, 1.0 - (dist - config.VERY_CLOSE_DISTANCE_A) / span)


def _localized_proximity_mask(shape, idx_a, idx_b, voxel_size_xyz, cutoff):
    xyz_a = np.column_stack(idx_a).astype(float)[:, ::-1] * voxel_size_xyz
    xyz_b = np.column_stack(idx_b).astype(float)[:, ::-1] * voxel_size_xyz
    if len(xyz_a) == 0 or len(xyz_b) == 0:
        return np.zeros(shape, dtype=bool)
    d_ab, _ = cKDTree(xyz_b).query(xyz_a, k=1, workers=-1)
    d_ba, _ = cKDTree(xyz_a).query(xyz_b, k=1, workers=-1)
    mask = np.zeros(shape, dtype=bool)
    keep_a = d_ab <= cutoff
    keep_b = d_ba <= cutoff
    if np.any(keep_a):
        mask[tuple(arr[keep_a] for arr in idx_a)] = True
    if np.any(keep_b):
        mask[tuple(arr[keep_b] for arr in idx_b)] = True
    return mask


def _pair_pocket_mask(shape, comp_a, comp_b, voxel_size_xyz):
    ov_nvox, ov_mask = _overlap_voxels(shape, comp_a["indices"], comp_b["indices"])
    if ov_nvox > 0:
        return ov_mask, ov_nvox, 0.0
    dist = _min_distance(comp_a["indices"], comp_b["indices"], voxel_size_xyz)
    bonus = _distance_bonus(dist)
    if bonus is None:
        return None, 0, None
    prox_mask = _localized_proximity_mask(
        shape, comp_a["indices"], comp_b["indices"], voxel_size_xyz, config.CLOSE_DISTANCE_A)
    if not np.any(prox_mask):
        return None, 0, None
    return prox_mask, 0, dist


def _field_integral_in_mask(data, mask, field):
    vals = data[mask]
    vals = vals[np.isfinite(vals)]
    if len(vals) == 0:
        return 0.0
    return float(np.sum(np.abs(vals)) if field == "apbs" else np.sum(vals))


def _relevance_scores(mask, stk_data, hyd_data, apbs_data):
    totals = {
        "stacking": _field_integral_in_mask(stk_data, np.isfinite(stk_data), "stacking"),
        "hydrophobic": _field_integral_in_mask(hyd_data, np.isfinite(hyd_data), "hydrophobic"),
        "apbs": _field_integral_in_mask(apbs_data, np.isfinite(apbs_data), "apbs"),
    }
    in_mask = {
        "stacking": _field_integral_in_mask(stk_data, mask, "stacking"),
        "hydrophobic": _field_integral_in_mask(hyd_data, mask, "hydrophobic"),
        "apbs": _field_integral_in_mask(apbs_data, mask, "apbs"),
    }
    return {
        f"{k}_rel": (in_mask[k] / totals[k] if totals[k] > 0 else 0.0)
        for k in totals
    }


def _summarize_pocket(mask, pocket_type, atom_xyz, stk_data, hyd_data, apbs_data, grid: Grid):
    if mask is None or not np.any(mask):
        return None
    coords = np.column_stack(np.where(mask))
    pocket_xyz = indices_to_xyz(tuple(coords[:, i] for i in range(3)), grid)
    buriedness = _estimate_real_buriedness(pocket_xyz, atom_xyz)
    relevance = _relevance_scores(mask, stk_data, hyd_data, apbs_data)
    score = (
        config.POCKET_SCORE_WEIGHTS["stacking_rel"] * relevance["stacking_rel"] +
        config.POCKET_SCORE_WEIGHTS["hydrophobic_rel"] * relevance["hydrophobic_rel"] +
        config.POCKET_SCORE_WEIGHTS["apbs_rel"] * relevance["apbs_rel"] +
        config.POCKET_SCORE_WEIGHTS["buriedness"] * buriedness
    )
    return {
        "pocket_type": pocket_type, "mask": mask,
        "centroid_xyz": pocket_xyz.mean(axis=0),
        "nvox": int(np.count_nonzero(mask)),
        "real_buriedness": buriedness,
        "pocket_score": float(score),
        **relevance,
    }


def _best_pair_pocket(comps_a, comps_b, shape, voxel_size_xyz, pocket_type,
                       atom_xyz, stk_data, hyd_data, apbs_data, grid):
    candidates = []
    for a in comps_a:
        for b in comps_b:
            mask, ov_nvox, dist = _pair_pocket_mask(shape, a, b, voxel_size_xyz)
            if mask is None:
                continue
            pocket = _summarize_pocket(mask, pocket_type, atom_xyz, stk_data, hyd_data, apbs_data, grid)
            if pocket is None or pocket["real_buriedness"] < config.REAL_BURIEDNESS_MIN:
                continue
            candidates.append((pocket["nvox"], pocket["pocket_score"], pocket))
    if not candidates:
        return None
    candidates.sort(key=lambda t: (t[0], t[1]), reverse=True)
    return candidates[0][2]


def build_candidate_pockets(field_data: dict, isovalues: dict, atom_xyz) -> list:
    """field_data: {"stacking": Grid, "hydrophobic": Grid, "apbs": Grid}."""
    required = ("stacking", "hydrophobic", "apbs")
    if not all(f in field_data and f in isovalues for f in required):
        return []

    stk_grid, hyd_grid, apbs_grid = (field_data[f] for f in required)
    shape = stk_grid.shape
    voxel_size_xyz = stk_grid.voxel_size

    stk_mask = threshold_mask(stk_grid.data, isovalues["stacking"], "stacking")
    hyd_mask = threshold_mask(hyd_grid.data, isovalues["hydrophobic"], "hydrophobic")
    apbs_mask = threshold_mask(apbs_grid.data, isovalues["apbs"], "apbs")

    stk_labels, stk_n = connected_components(stk_mask)
    hyd_labels, hyd_n = connected_components(hyd_mask)
    apbs_labels, apbs_n = connected_components(apbs_mask)

    stk_comps = component_stats(stk_labels, stk_n, stk_grid.data, stk_grid, atom_xyz, "stacking")
    hyd_comps = component_stats(hyd_labels, hyd_n, hyd_grid.data, hyd_grid, atom_xyz, "hydrophobic")
    apbs_comps = component_stats(apbs_labels, apbs_n, apbs_grid.data, apbs_grid, atom_xyz, "apbs")

    args = (atom_xyz, stk_grid.data, hyd_grid.data, apbs_grid.data, stk_grid)
    pockets = []

    # mixed_fields: best stacking+hydrophobic+apbs triple overlap / proximity union
    best_mixed = None
    for s in stk_comps:
        for h in hyd_comps:
            for a in apbs_comps:
                tri_mask = (_component_mask(shape, s["indices"]) &
                            _component_mask(shape, h["indices"]) &
                            _component_mask(shape, a["indices"]))
                mask = tri_mask if np.any(tri_mask) else _union_mask(shape, [s, h, a])
                pocket = _summarize_pocket(mask, "mixed_fields", *args)
                if pocket is None or pocket["real_buriedness"] < config.REAL_BURIEDNESS_MIN:
                    continue
                if best_mixed is None or (pocket["nvox"], pocket["pocket_score"]) > \
                        (best_mixed["nvox"], best_mixed["pocket_score"]):
                    best_mixed = pocket
    if best_mixed is not None:
        pockets.append(best_mixed)

    best_se = _best_pair_pocket(stk_comps, apbs_comps, shape, voxel_size_xyz,
                                 "stacking_electrostatic", *args)
    if best_se is not None:
        pockets.append(best_se)

    best_sh = _best_pair_pocket(stk_comps, hyd_comps, shape, voxel_size_xyz,
                                 "stacking_hydrophobic", *args)
    if best_sh is not None:
        pockets.append(best_sh)

    if apbs_comps:
        pocket = _summarize_pocket(_union_mask(shape, apbs_comps), "electrostatic", *args)
        if pocket is not None:
            pockets.append(pocket)

    return pockets
