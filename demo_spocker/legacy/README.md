These are the original, unmodified scripts from the two ad hoc pipelines
this project started from (whole-structure hotspot/pocket detection, and
non-canonical-residue hydrogen-bond pocket detection). They are kept for
reference only and are not run by anything in this repo.

`../pipeline/` is the maintained replacement: a single, modular pipeline
(driven by `../1_run_pipeline.py`) that covers the same ground. Notably, it
targets the current `volgrids` CLI (these scripts were written against an
older, incompatible CLI: e.g. `volgrids smiffer rna ...` and
`DO_SMIF_HYDROPHILIC`-style config keys no longer exist), and fixes a
voxel-index/Cartesian-axis mixup present in parts of the original scoring and
trimming code.
