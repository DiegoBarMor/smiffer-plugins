"""
Pick a per-field isovalue (stacking, hydrophobic, apbs) to threshold at when
building candidate pockets in hotspots.py.

Stacking/hydrophobic: the isovalue is where the log-count histogram's slope
(1st derivative) is most negative beyond a fixed floor -- i.e. where the
field's density distribution falls off a cliff, separating "hotspot" voxels
from background noise.

APBS (electrostatics, more negative = more favorable): the isovalue is the
first non-trivial density peak on the left side of the histogram, ranked
outward from a defined start -- with a fallback to the middle of a
plausible voxel-count band when no peak survives the search window.
"""

import numpy as np
from scipy.signal import find_peaks, savgol_filter

from . import config


def _load_field_values(grid, field):
    vol = grid.data.astype(np.float32).ravel()
    vol = vol[np.isfinite(vol)]
    if field in ("stacking", "hydrophobic"):
        return vol[vol > 0]
    return vol[vol < config.ELE_MAX_NEGATIVE_VALUE]


def _choose_bins(values, field):
    if len(values) < 100:
        return 80
    return 240 if field == "apbs" else 180


def _smooth_histogram(values, bins):
    counts, edges = np.histogram(values, bins=bins)
    centers = (edges[:-1] + edges[1:]) / 2.0
    log_counts = np.log10(counts + 1.0)
    if len(log_counts) < 7:
        return None
    win = min(21, len(log_counts) if len(log_counts) % 2 == 1 else len(log_counts) - 1)
    if win < 5:
        return None
    smooth = savgol_filter(log_counts, window_length=win, polyorder=3)
    deriv1 = np.gradient(smooth, centers)
    return counts, centers, smooth, deriv1


def _pick_slope_minimum(centers, deriv1, threshold_x):
    mask = np.isfinite(centers) & np.isfinite(deriv1) & (centers >= threshold_x)
    if not np.any(mask):
        return None
    c, d = centers[mask], deriv1[mask]
    idx = int(np.argmin(d))
    return float(c[idx])


def _band_midpoint_fallback(centers, counts, count_min, count_max):
    band = (counts >= count_min) & (counts <= count_max)
    if np.any(band):
        idxs = np.where(band)[0]
        return float(centers[idxs[len(idxs) // 2]])
    return float(centers[int(np.argmax(counts))])


def _pick_apbs_peak(centers, counts, smooth):
    mask = np.isfinite(centers) & np.isfinite(counts) & np.isfinite(smooth) & \
        (centers <= config.ELE_SEARCH_UP_TO)
    if np.count_nonzero(mask) < 7:
        return None

    c, h, s = centers[mask], counts[mask], smooth[mask]
    order = np.argsort(c)
    c, h, s = c[order], h[order], s[order]

    dynamic_range = float(np.max(s) - np.min(s))
    if dynamic_range <= 0:
        return _band_midpoint_fallback(c, h, config.ELE_MIN_PEAK_COUNT, config.ELE_MAX_PEAK_COUNT)

    prominence = max(config.ELE_MIN_ABS_PROM, config.ELE_MIN_PROM_FRAC * dynamic_range)
    distance = max(1, len(s) // 40)
    peaks, _ = find_peaks(s, prominence=prominence, distance=distance)
    if len(peaks) == 0:
        peaks, _ = find_peaks(s, distance=distance)
    if len(peaks) == 0:
        return _band_midpoint_fallback(c, h, config.ELE_MIN_PEAK_COUNT, config.ELE_MAX_PEAK_COUNT)

    peak_positions = np.sort(c[peaks])
    peak_counts = h[np.searchsorted(c, peak_positions)]
    in_band = (peak_counts >= config.ELE_MIN_PEAK_COUNT) & (peak_counts <= config.ELE_MAX_PEAK_COUNT)
    if np.any(in_band):
        return float(peak_positions[np.argmax(in_band)])

    return _band_midpoint_fallback(c, h, config.ELE_MIN_PEAK_COUNT, config.ELE_MAX_PEAK_COUNT)


def _pick_apbs_fallback_from_full_distribution(grid):
    vol = grid.data.astype(np.float32).ravel()
    vol = vol[np.isfinite(vol) & (vol < 0)]
    if len(vol) < config.MIN_VALUES_FOR_HISTOGRAM:
        return None
    result = _smooth_histogram(vol, _choose_bins(vol, "apbs"))
    if result is None:
        return None
    counts, centers, _, _ = result
    return _band_midpoint_fallback(centers, counts,
                                    config.ELE_FALLBACK_COUNT_MIN, config.ELE_FALLBACK_COUNT_MAX)


def pick_isovalues(field_data: dict) -> dict:
    """field_data: {"stacking": Grid, "hydrophobic": Grid, "apbs": Grid}
    (missing fields are simply skipped). Returns {field: isovalue}."""
    isovalues = {}
    for field in config.ISO_FIELDS:
        grid = field_data.get(field)
        if grid is None:
            continue

        values = _load_field_values(grid, field)
        if len(values) < config.MIN_VALUES_FOR_HISTOGRAM:
            continue

        result = _smooth_histogram(values, _choose_bins(values, field))
        if result is None:
            continue
        counts, centers, smooth, deriv1 = result

        if field in ("stacking", "hydrophobic"):
            iso = _pick_slope_minimum(centers, deriv1, config.ISO_MARK_THRESHOLD[field])
        else:
            iso = _pick_apbs_peak(centers, counts, smooth)
            if iso is None:
                iso = _pick_apbs_fallback_from_full_distribution(grid)

        if iso is not None:
            isovalues[field] = iso

    return isovalues
