These are the original scripts from the two ad hoc pipelines this project
started from (whole-structure hotspot/pocket detection, and
non-canonical-residue hydrogen-bond pocket detection). They are kept for
reference and as a baseline to compare `../pipeline/`'s output against, via
`../run_pipeline_legacy.sh <input.pdb> <output_dir>`.

Their algorithms are untouched. The only edits made are to the hardcoded
BASE / PDB_BASE / BASE_DIR / ANALYSIS_DIR / HBOND_BASE path constants at the
top of each script: they used to point at one absolute path
(`/media/gio/.../SMIFs_Analysis_All_PDBs`) that only ever existed on the
original author's machine. They now resolve relative to this file
(`Path(__file__).resolve().parents[1] / "testdata" / "legacy_work" / ...`),
i.e. `demo_spocker/testdata/legacy_work/`, which `run_pipeline_legacy.sh`
populates before running these scripts and removes afterwards.

`../pipeline/` is the maintained replacement: a single, modular pipeline
(driven by `../1_run_pipeline.py`) that covers the same ground. Notably, it
targets the current `volgrids` CLI (these scripts were written against an
older, incompatible CLI: e.g. `volgrids smiffer rna ...` and
`DO_SMIF_HYDROPHILIC`-style config keys no longer exist), and fixes a
voxel-index/Cartesian-axis mixup present in parts of the original scoring and
trimming code.
