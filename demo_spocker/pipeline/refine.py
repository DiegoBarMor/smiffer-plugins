"""
Turn a candidate pocket mask (from hotspots.py or hbond_pockets.py) into a
final pocket volume: pick the largest connected patch, find a geometric seed
point buried inside it, grow a sphere around that seed, carve out anything
within ATOM_EXCLUSION_RADIUS_A of an RNA heavy atom, and keep only the
fragment connected to the seed.
"""

import numpy as np
from scipy import ndimage

from . import config
from .mrc_io import Grid, xyz_to_voxel_index


def _connectivity_structure(connectivity):
    return ndimage.generate_binary_structure(3, connectivity)


def _choose_single_patch(mask, voxel_volume_a3, conn):
    labels, nlab = ndimage.label(mask, structure=_connectivity_structure(conn))
    if nlab == 0:
        return None
    counts = np.bincount(labels.ravel())
    largest_label = int(np.argmax(counts[1:]) + 1)
    return labels == largest_label


def _choose_seed_center(mask, grid: Grid):
    idx = np.column_stack(np.where(mask))  # (iz, iy, ix)
    if len(idx) == 0:
        return None, None

    voxel_size_zyx = grid.voxel_size[::-1]
    dist = ndimage.distance_transform_edt(mask, sampling=voxel_size_zyx)
    dist_vals = dist[tuple(idx.T)]
    max_dist = float(dist_vals.max())

    def idx_to_xyz(ix_arr):
        iz, iy, ix = ix_arr[:, 0], ix_arr[:, 1], ix_arr[:, 2]
        return np.column_stack([
            grid.origin[0] + ix * grid.voxel_size[0],
            grid.origin[1] + iy * grid.voxel_size[1],
            grid.origin[2] + iz * grid.voxel_size[2],
        ])

    if max_dist <= 0.0:
        pts = idx_to_xyz(idx)
        cog = pts.mean(axis=0)
        best = int(np.argmin(np.sum((pts - cog) ** 2, axis=1)))
        return idx[best], pts[best]

    cutoff = float(np.percentile(dist_vals, config.CENTER_CORE_PERCENTILE))
    candidate_idx = idx[dist_vals >= cutoff]
    if len(candidate_idx) == 0:
        best = int(np.argmax(dist_vals))
        center_idx = idx[best]
        return center_idx, idx_to_xyz(center_idx[None, :])[0]

    patch_pts = idx_to_xyz(idx)
    if len(patch_pts) > config.MAX_PATCH_SAMPLES:
        sel = np.linspace(0, len(patch_pts) - 1, config.MAX_PATCH_SAMPLES).astype(int)
        patch_pts = patch_pts[sel]

    cand_pts = idx_to_xyz(candidate_idx)
    mean_d2 = ((cand_pts[:, None, :] - patch_pts[None, :, :]) ** 2).sum(axis=2).mean(axis=1)
    clearance = dist[tuple(candidate_idx.T)]
    max_clear = float(clearance.max())
    penalty = (max_clear - clearance) / (max_clear + 1e-12)
    scores = mean_d2 + penalty * (np.min(voxel_size_zyx) ** 2)
    best = int(np.argmin(scores))
    return candidate_idx[best], cand_pts[best]


def _build_seed_sphere(center_xyz, grid: Grid, radius_a):
    nz, ny, nx = grid.shape
    ciz, ciy, cix = xyz_to_voxel_index(center_xyz, grid)
    rz, ry, rx = (radius_a / grid.voxel_size[2],
                  radius_a / grid.voxel_size[1],
                  radius_a / grid.voxel_size[0])
    iz_lo, iz_hi = max(0, int(np.floor(ciz - rz))), min(nz - 1, int(np.ceil(ciz + rz)))
    iy_lo, iy_hi = max(0, int(np.floor(ciy - ry))), min(ny - 1, int(np.ceil(ciy + ry)))
    ix_lo, ix_hi = max(0, int(np.floor(cix - rx))), min(nx - 1, int(np.ceil(cix + rx)))

    mask = np.zeros(grid.shape, dtype=bool)
    iz_g, iy_g, ix_g = np.meshgrid(
        np.arange(iz_lo, iz_hi + 1), np.arange(iy_lo, iy_hi + 1), np.arange(ix_lo, ix_hi + 1),
        indexing="ij")
    x = grid.origin[0] + ix_g * grid.voxel_size[0]
    y = grid.origin[1] + iy_g * grid.voxel_size[1]
    z = grid.origin[2] + iz_g * grid.voxel_size[2]
    dist2 = (x - center_xyz[0]) ** 2 + (y - center_xyz[1]) ** 2 + (z - center_xyz[2]) ** 2
    mask[iz_lo:iz_hi + 1, iy_lo:iy_hi + 1, ix_lo:ix_hi + 1] = dist2 <= radius_a ** 2
    return mask


def _trim_by_atoms(sphere_mask, atom_xyz, grid: Grid, excl_radius_a):
    if len(atom_xyz) == 0:
        return sphere_mask
    nz, ny, nx = sphere_mask.shape
    r2 = excl_radius_a ** 2
    rz, ry, rx = (excl_radius_a / grid.voxel_size[2],
                  excl_radius_a / grid.voxel_size[1],
                  excl_radius_a / grid.voxel_size[0])

    for ax, ay, az in atom_xyz:
        ciz, ciy, cix = xyz_to_voxel_index((ax, ay, az), grid)
        iz_lo, iz_hi = max(0, int(np.floor(ciz - rz))), min(nz - 1, int(np.ceil(ciz + rz)))
        iy_lo, iy_hi = max(0, int(np.floor(ciy - ry))), min(ny - 1, int(np.ceil(ciy + ry)))
        ix_lo, ix_hi = max(0, int(np.floor(cix - rx))), min(nx - 1, int(np.ceil(cix + rx)))
        if iz_lo > iz_hi or iy_lo > iy_hi or ix_lo > ix_hi:
            continue
        sub = sphere_mask[iz_lo:iz_hi + 1, iy_lo:iy_hi + 1, ix_lo:ix_hi + 1]
        if not sub.any():
            continue
        iz_g, iy_g, ix_g = np.meshgrid(
            np.arange(iz_lo, iz_hi + 1), np.arange(iy_lo, iy_hi + 1), np.arange(ix_lo, ix_hi + 1),
            indexing="ij")
        x = grid.origin[0] + ix_g * grid.voxel_size[0]
        y = grid.origin[1] + iy_g * grid.voxel_size[1]
        z = grid.origin[2] + iz_g * grid.voxel_size[2]
        dist2 = (x - ax) ** 2 + (y - ay) ** 2 + (z - az) ** 2
        sphere_mask[iz_lo:iz_hi + 1, iy_lo:iy_hi + 1, ix_lo:ix_hi + 1][(dist2 <= r2) & sub] = False
    return sphere_mask


def _extract_fragment_near_center(trimmed_mask, center_xyz, center_idx, grid: Grid, connectivity):
    labeled, n_labels = ndimage.label(trimmed_mask, structure=_connectivity_structure(connectivity))
    if n_labels == 0:
        return None
    if n_labels == 1:
        return trimmed_mask

    iz_c, iy_c, ix_c = (int(np.clip(v, 0, s - 1)) for v, s in zip(center_idx, grid.shape))
    centre_label = int(labeled[iz_c, iy_c, ix_c])
    if centre_label != 0:
        return labeled == centre_label

    best_dist, best_label = np.inf, -1
    for lab in range(1, n_labels + 1):
        zi, yi, xi = np.where(labeled == lab)
        cx = grid.origin[0] + xi.mean() * grid.voxel_size[0]
        cy = grid.origin[1] + yi.mean() * grid.voxel_size[1]
        cz = grid.origin[2] + zi.mean() * grid.voxel_size[2]
        dist = float(np.sqrt((cx - center_xyz[0]) ** 2 + (cy - center_xyz[1]) ** 2 + (cz - center_xyz[2]) ** 2))
        if dist < best_dist:
            best_dist, best_label = dist, lab
    return labeled == best_label


def refine_pocket(mask: np.ndarray, grid: Grid, atom_xyz) -> np.ndarray:
    """Return the final, atom-trimmed pocket mask, or None if nothing survives."""
    if mask is None or not np.any(mask):
        return None

    chosen = _choose_single_patch(mask, grid.voxel_volume_a3, config.PATCH_CONNECTIVITY)
    if chosen is None:
        return None

    center_idx, center_xyz = _choose_seed_center(chosen, grid)
    if center_idx is None:
        return None

    sphere_mask = _build_seed_sphere(center_xyz, grid, config.SEED_SPHERE_RADIUS_A)
    if not np.any(sphere_mask):
        return None

    sphere_mask = _trim_by_atoms(sphere_mask, atom_xyz, grid, config.ATOM_EXCLUSION_RADIUS_A)
    if not np.any(sphere_mask):
        return None

    return _extract_fragment_near_center(sphere_mask, center_xyz, center_idx, grid,
                                          config.POCKET_CONNECTIVITY)
