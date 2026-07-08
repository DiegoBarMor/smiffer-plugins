# SPOCKER

Identifies RNA binding pockets from a PDB structure, using
[volgrids](https://github.com/diegobarmor/volgrids) SMIF fields.

1) Create the conda environment: `conda env create -f demo_spocker/environment.yml`
2) Run with `bash demo_spocker/run.sh` (cwd must be the root directory of the repo).

`run.sh` chains two steps, which can also be run standalone:

- `0_prepare_input.sh <PDB_ID>`: downloads a structure from RCSB, repairs it
  with pdbfixer, and strips it down to nucleic-acid residues only. Writes
  `demo_spocker/testdata/input/<PDB_ID>.nucl.pdb`.
- `1_run_pipeline.py <input.pdb> <output_dir>`: generates SMIF fields and
  writes ranked pocket grids (`<pdb_id>.Pocket1.mrc`, ...) plus a text
  summary to `<output_dir>`. See `pipeline/` for the pipeline's modules and
  `pipeline/config.py` for its tunable parameters.

`legacy/` holds the original, single-use scripts `pipeline/` replaces; see
`legacy/README.md`.
