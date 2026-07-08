"""
MRC grid I/O, shared by every other module so there is exactly one place
that knows how mrcfile's axis ordering maps to Cartesian coordinates.

mrcfile loads volumetric data as a numpy array of shape (nz, ny, nx): axis 0
is the slowest-varying "section" axis (Z), axis 1 is "row" (Y), axis 2 is
"column" (X). ``mrc.voxel_size`` and ``mrc.header.origin`` are given in
Cartesian (x, y, z) order. Mixing these two orderings up (e.g. multiplying a
(z, y, x) index tuple directly by a (vx, vy, vz) voxel-size vector) silently
swaps the X and Z axes -- a bug present in parts of the original scripts this
package replaces. All index<->coordinate conversions go through
`indices_to_xyz` / `xyz_to_voxel_index` below to avoid repeating that mistake.
"""

from dataclasses import dataclass

import mrcfile
import numpy as np


@dataclass
class Grid:
    data: np.ndarray            # shape (nz, ny, nx)
    voxel_size: np.ndarray       # (vx, vy, vz), angstrom
    origin: np.ndarray          # (ox, oy, oz), angstrom

    @property
    def shape(self):
        return self.data.shape

    @property
    def voxel_volume_a3(self) -> float:
        return float(np.prod(self.voxel_size))


def load_mrc(path) -> Grid:
    with mrcfile.open(str(path), mode="r", permissive=True) as mrc:
        data = np.asarray(mrc.data, dtype=np.float32).copy()
        voxel_size = np.array(
            [float(mrc.voxel_size.x), float(mrc.voxel_size.y), float(mrc.voxel_size.z)],
            dtype=np.float64,
        )
        try:
            origin = np.array(
                [float(mrc.header.origin.x), float(mrc.header.origin.y), float(mrc.header.origin.z)],
                dtype=np.float64,
            )
        except Exception:
            origin = np.zeros(3, dtype=np.float64)
        if np.allclose(origin, 0.0):
            try:
                origin = np.array(
                    [
                        int(mrc.header.nxstart) * voxel_size[0],
                        int(mrc.header.nystart) * voxel_size[1],
                        int(mrc.header.nzstart) * voxel_size[2],
                    ],
                    dtype=np.float64,
                )
            except Exception:
                pass
    return Grid(data=data, voxel_size=voxel_size, origin=origin)


def save_mrc(path, data: np.ndarray, grid: Grid) -> None:
    out = np.asarray(data, dtype=np.float32)
    with mrcfile.new(str(path), overwrite=True) as mrc:
        mrc.set_data(out)
        mrc.voxel_size = tuple(float(v) for v in grid.voxel_size)
        try:
            mrc.header.origin.x = float(grid.origin[0])
            mrc.header.origin.y = float(grid.origin[1])
            mrc.header.origin.z = float(grid.origin[2])
        except Exception:
            pass
        mrc.update_header_from_data()
        mrc.update_header_stats()


def indices_to_xyz(idx_zyx, grid: Grid) -> np.ndarray:
    """Convert a (iz, iy, ix) index tuple (as returned by np.where) to an
    (N, 3) array of Cartesian XYZ voxel-center coordinates."""
    iz, iy, ix = (np.asarray(a, dtype=float) for a in idx_zyx)
    x = grid.origin[0] + ix * grid.voxel_size[0]
    y = grid.origin[1] + iy * grid.voxel_size[1]
    z = grid.origin[2] + iz * grid.voxel_size[2]
    return np.column_stack([x, y, z])


def xyz_to_voxel_index(xyz, grid: Grid):
    """Convert one (x, y, z) Cartesian point to a (iz, iy, ix) float index."""
    x, y, z = float(xyz[0]), float(xyz[1]), float(xyz[2])
    ix = (x - grid.origin[0]) / grid.voxel_size[0]
    iy = (y - grid.origin[1]) / grid.voxel_size[1]
    iz = (z - grid.origin[2]) / grid.voxel_size[2]
    return iz, iy, ix
