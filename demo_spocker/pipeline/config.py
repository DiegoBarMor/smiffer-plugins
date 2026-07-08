"""
Tunable parameters for the pocket-detection pipeline, grouped by stage.
Edit values here rather than hunting through the pipeline modules.
"""

# ── Field generation (pipeline/fields.py) ───────────────────────────────────
# Config keys match volgrids==1.0.0 (see demo_spocker/environment.yml).
# Fields computed for the whole structure. "hphil" (hydrophilic) is generated
# by volgrids but never used by pocket detection below, so it stays off.
WHOLE_STRUCTURE_CONFIG = {
    "SMIF_HPHIL": "false",
}

# Fields computed for the non-canonical-residue subset (hydrogen-bond pockets).
HBOND_SUBSET_CONFIG = {
    "SMIF_APBS": "true",
    "SMIF_HBA": "true",
    "SMIF_HBD": "true",
    "SMIF_HPHIL": "false",
    "SMIF_HPHOB": "false",
    "SMIF_STK": "false",
    "SMIF_HB_ONLY_NBASE": "true",
}

# ── Isovalue selection (pipeline/isovalues.py) ──────────────────────────────
ISO_FIELDS = ("stacking", "hydrophobic", "apbs")
ISO_MARK_THRESHOLD = {"stacking": 1.0, "hydrophobic": 5.0}

ELE_SEARCH_UP_TO = -17.5
ELE_MAX_NEGATIVE_VALUE = -0.05
ELE_MIN_PROM_FRAC = 0.01
ELE_MIN_ABS_PROM = 0.008
ELE_MIN_PEAK_COUNT = 100
ELE_MAX_PEAK_COUNT = 10000
ELE_FALLBACK_COUNT_MIN = 100
ELE_FALLBACK_COUNT_MAX = 1000

MIN_VALUES_FOR_HISTOGRAM = 20

# ── Candidate pocket hotspots (pipeline/hotspots.py) ────────────────────────
MIN_COMPONENT_VOXELS = 8
CLOSE_DISTANCE_A = 3.5
VERY_CLOSE_DISTANCE_A = 1.5
REAL_BURIEDNESS_RADIUS_A = 2.5
REAL_BURIEDNESS_NEIGHBOR_RADIUS_A = 10.0
REAL_BURIEDNESS_MIN = 0.20
ACCESSIBLE_POINT_FAR_A = 3.0
CENTROID_ENCLOSURE_RADIUS_A = 8.0

POCKET_SCORE_WEIGHTS = {
    "stacking_rel": 1.0,
    "hydrophobic_rel": 1.0,
    "apbs_rel": 1.0,
    "buriedness": 1.2,
}

# ── Pocket volume refinement (pipeline/refine.py) ───────────────────────────
SEED_SPHERE_RADIUS_A = 8.0
ATOM_EXCLUSION_RADIUS_A = 3.0
PATCH_CONNECTIVITY = 2   # 6-connectivity when picking the initial candidate patch
POCKET_CONNECTIVITY = 3  # 26-connectivity when isolating the final fragment
CENTER_CORE_PERCENTILE = 95.0
MAX_PATCH_SAMPLES = 4000

# ── Hydrogen-bond pockets (pipeline/hbond_pockets.py) ───────────────────────
HB_INTENSITY_PERCENTILE = 50
HBOND_OVERLAP_EXPAND_VOXELS = 1
HBOND_MIN_SITE_SEPARATION_A = 10.0
HBOND_CLUSTER_CONNECTIVITY = 2
HBOND_MAX_SITES = 2
HBOND_MIN_SITE_VOXELS = 10

# ── Unique pocket merging & scoring (pipeline/unique_pockets.py) ────────────
SIGNIFICANT_OVERLAP_FRACTION = 0.20
RNA_TRIM_CUTOFF_A = 5.0
TERMINAL_ZONE_CUTOFF_A = 5.0
TERMINAL_VOXEL_FRACTION = 0.60
APBS_RNA_KEEP_CUTOFF_A = 5.0
