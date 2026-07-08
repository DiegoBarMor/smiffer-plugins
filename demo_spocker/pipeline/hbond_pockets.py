"""
Detect hydrogen-bond pockets around non-canonical residues: voxels where the
electrostatic (apbs), H-bond acceptor (hba) and H-bond donor (hbd) fields all
overlap, clustered into up to HBOND_MAX_SITES spatially separated sites.

Operates on the residue-subset fields produced by
fields.compute_hbond_subset_fields (see pipeline.run).
"""

import numpy as np
from scipy.ndimage import binary_dilation, generate_binary_structure, label

from . import config
from .mrc_io import Grid, indices_to_xyz

ELE_CONSTANT = -2.0


def _ele_isovalue(ele_data):
    nonzero = ele_data[ele_data != 0.0]
    if len(nonzero) == 0:
        return ELE_CONSTANT
    return float((nonzero.min() + nonzero.max()) / 2.0 + ELE_CONSTANT)


def _threshold_hb_field(data, percentile=config.HB_INTENSITY_PERCENTILE):
    nonzero = data[data != 0.0]
    if len(nonzero) == 0:
        return np.zeros(data.shape, dtype=bool)
    threshold = np.percentile(np.abs(nonzero), percentile)
    return np.abs(data) >= threshold


def _dilate(mask, iterations):
    if iterations <= 0:
        return mask.copy()
    structure = np.ones((2 * iterations + 1,) * 3, dtype=bool)
    return binary_dilation(mask, structure=structure)


def find_hbond_sites(hb_field_data: dict) -> list:
    """hb_field_data: {"apbs": Grid, "hba": Grid, "hbd": Grid} (residue-subset
    fields, all sharing the same grid). Returns up to HBOND_MAX_SITES dicts
    of {"mask", "centroid_xyz", "nvox"}, largest first, mutually separated
    by at least HBOND_MIN_SITE_SEPARATION_A."""
    if not all(f in hb_field_data for f in ("apbs", "hba", "hbd")):
        return []

    ele: Grid = hb_field_data["apbs"]
    hba: Grid = hb_field_data["hba"]
    hbd: Grid = hb_field_data["hbd"]
    if ele.shape != hba.shape or ele.shape != hbd.shape:
        return []

    isovalue = _ele_isovalue(ele.data)
    ele_mask = np.isfinite(ele.data) & (ele.data <= isovalue)
    hba_mask = _threshold_hb_field(hba.data)
    hbd_mask = _threshold_hb_field(hbd.data)
    if not np.any(hba_mask) or not np.any(hbd_mask):
        return []

    overlap = (_dilate(ele_mask, config.HBOND_OVERLAP_EXPAND_VOXELS) &
               _dilate(hba_mask, config.HBOND_OVERLAP_EXPAND_VOXELS) &
               _dilate(hbd_mask, config.HBOND_OVERLAP_EXPAND_VOXELS) &
               ele_mask)
    if not np.any(overlap):
        return []

    structure = generate_binary_structure(3, config.HBOND_CLUSTER_CONNECTIVITY)
    labeled, n_labels = label(overlap, structure=structure)

    candidates = []
    for lab in range(1, n_labels + 1):
        comp_mask = labeled == lab
        nvox = int(np.count_nonzero(comp_mask))
        if nvox < config.HBOND_MIN_SITE_VOXELS:
            continue
        centroid = indices_to_xyz(np.where(comp_mask), ele).mean(axis=0)
        candidates.append({"mask": comp_mask, "nvox": nvox, "centroid_xyz": centroid})
    candidates.sort(key=lambda c: -c["nvox"])
    if not candidates:
        return []

    sites = [candidates[0]]
    for cand in candidates[1:]:
        if len(sites) >= config.HBOND_MAX_SITES:
            break
        if all(np.linalg.norm(cand["centroid_xyz"] - s["centroid_xyz"]) >= config.HBOND_MIN_SITE_SEPARATION_A
               for s in sites):
            sites.append(cand)
    return sites
