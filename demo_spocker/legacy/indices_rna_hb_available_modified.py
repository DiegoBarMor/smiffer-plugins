import sys
import io
import logging
import warnings
import re
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
import MDAnalysis as mda
import pandas as pd

from rnapolis.annotator import (
    extract_base_interactions,
    handle_input_file,
    read_3d_structure,
    write_csv,
)

# ------------------------------------------------------------------------------
def run_rnapolis(path_pdb: Path, path_csv: Path):
    """
    Run RNApolis annotation. If annotation fails entirely, write an empty CSV
    so that downstream functions receive a valid (empty) file rather than
    crashing. The warning is printed so the user knows annotation was skipped.
    """
    try:
        file = handle_input_file(path_pdb)
        structure3d = read_3d_structure(file, None)
        base_interactions = extract_base_interactions(structure3d)
        structure2d, _ = structure3d.extract_secondary_structure(
            base_interactions, False, False
        )
        write_csv(path_csv, structure2d)
    except Exception as e:
        # Do NOT silently swallow — warn visibly, then write empty CSV
        print(f"[WARNING] RNApolis annotation failed ({e}); "
              f"all residues will be treated as non-canonical.", file=sys.stderr)
        pd.DataFrame(
            columns=["type", "classification-1", "classification-2", "nt1", "nt2"]
        ).to_csv(path_csv, index=False)


# ------------------------------------------------------------------------------
def _parse_resid(nt_label: str):
    """
    Robustly extract the residue number from an RNApolis nt label.

    Observed formats:
      "A.123"     → 123   (chain . resid)
      "A.123A"    → 123   (chain . resid + insertion code)
      "A.G.123"   → 123   (chain . resname . resid)
      "123"       → 123   (no chain ID)
      ".123"      → 123   (empty chain ID)

    Strategy: take the LAST contiguous run of digits in the label.
    This is robust to any prefix length, insertion codes, and missing chains.
    """
    # NOTE: single backslash inside r-string — do NOT double-escape
    m = re.search(r'(\d+)\D*$', nt_label)
    if m:
        return int(m.group(1))
    return None


# ------------------------------------------------------------------------------
def get_idxs_canonical(path_csv: Path) -> set:
    try:
        df = pd.read_csv(path_csv)
    except Exception:
        return set()

    # Guard against missing columns (e.g. empty CSV written on RNApolis failure)
    required = {"type", "classification-1", "classification-2", "nt1", "nt2"}
    if not required.issubset(df.columns):
        return set()

    df = df[
        (df["type"] == "base pair") &
        (df["classification-1"] == "cWW") &
        (
            (df["classification-2"] == "XIX") |
            (df["classification-2"] == "XX")
        )
    ]

    idxs_canonical = set()
    for col in ("nt1", "nt2"):
        for label in df[col].dropna():
            resid = _parse_resid(str(label))
            if resid is not None:
                idxs_canonical.add(resid)

    return idxs_canonical


# ------------------------------------------------------------------------------
def get_mda_universe_quiet(path_pdb) -> mda.Universe:
    buf = io.StringIO()
    logger = logging.getLogger("MDAnalysis")
    old_level = logger.getEffectiveLevel()
    try:
        logger.setLevel(logging.ERROR)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            with redirect_stdout(buf), redirect_stderr(buf):
                u = mda.Universe(str(path_pdb))
    finally:
        logger.setLevel(old_level)
    return u


# ------------------------------------------------------------------------------
def get_idxs_all_mda(path_pdb) -> set:
    """Primary path: use MDAnalysis to collect all residue sequence numbers."""
    u = get_mda_universe_quiet(path_pdb)
    return set(int(i) for i in u.residues.resids)


def get_idxs_all_manual(path_pdb) -> set:
    """
    Fallback: parse ATOM/HETATM lines directly from the PDB text.

    This is completely agnostic to:
      - Missing or blank chain IDs  (column 21, 0-based)
      - Non-standard residue names  (columns 17-20)
      - Malformed HEADER/CRYST records
    PDB column layout (1-based, fixed-width):
      cols  1- 6  record type
      cols 23-26  residue sequence number (resSeq)
    """
    idxs = set()
    with open(path_pdb, "r", errors="replace") as fh:
        for line in fh:
            if line[:6].strip() not in ("ATOM", "HETATM"):
                continue
            try:
                idxs.add(int(line[22:26].strip()))
            except ValueError:
                pass
    return idxs


def get_idxs_all(path_pdb) -> set:
    """
    Try MDAnalysis first; fall back to direct PDB parsing if it fails or
    returns an empty set (which can happen with non-standard residue names
    or missing chain IDs that confuse the MDAnalysis PDB reader).
    """
    try:
        idxs = get_idxs_all_mda(path_pdb)
        if idxs:
            return idxs
    except Exception as e:
        print(f"[WARNING] MDAnalysis failed ({e}); falling back to manual PDB parse.",
              file=sys.stderr)

    # Fallback — always works as long as the file has ATOM/HETATM lines
    return get_idxs_all_manual(path_pdb)


# ------------------------------------------------------------------------------
def main():
    run_rnapolis(PATH_PDB, PATH_CSV)
    idxs_canonical = get_idxs_canonical(PATH_CSV)
    idxs_all       = get_idxs_all(PATH_PDB)
    idxs_available = idxs_all - idxs_canonical
    print(' '.join(str(i) for i in sorted(idxs_available)))


################################################################################
if __name__ == "__main__":
    warnings.filterwarnings("ignore", module="MDAnalysis.*")
    PATH_PDB = Path(sys.argv[1])
    PATH_CSV = (Path(sys.argv[2]) if len(sys.argv) > 2
                else PATH_PDB.with_suffix(".csv"))
    main()
