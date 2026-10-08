"""Stage 1f: give every player file of the same kind the same columns and date format."""
import os

import pandas as pd

from .config import PLAYERS_DIR

FILE_SUFFIXES = ['_bat.csv', '_bowl.csv', '_field.csv']


def align_columns_and_dates(players_dir=PLAYERS_DIR):
    """Pad each file to the widest schema seen for its kind and normalize Start Date."""
    root_dir = players_dir
    suffixes = FILE_SUFFIXES

    # PASS 1: find the file with the most columns for each suffix
    max_info = {s: {'max_cols': 0, 'columns': [], 'file': None} for s in suffixes}

    for dirpath, _, filenames in os.walk(root_dir):
        for fname in filenames:
            for suf in suffixes:
                if fname.endswith(suf):
                    path = os.path.join(dirpath, fname)
                    try:
                        df = pd.read_csv(path)
                    except Exception:
                        continue
                    ncol = df.shape[1]
                    if ncol > max_info[suf]['max_cols']:
                        max_info[suf].update({
                            'max_cols': ncol,
                            'columns': df.columns.tolist(),
                            'file': path
                        })
                    break

    # PASS 2: enforce max-cols + normalize dates
    for dirpath, _, filenames in os.walk(root_dir):
        for fname in filenames:
            for suf in suffixes:
                if not fname.endswith(suf):
                    continue

                path = os.path.join(dirpath, fname)
                df = pd.read_csv(path)

                # Compare columns
                max_cols = max_info[suf]['columns']
                cur_cols = df.columns.tolist()

                missing = [c for c in max_cols if c not in cur_cols]
                extra   = [c for c in cur_cols   if c not in max_cols]

                # Add any missing columns (fill with NaN)
                for c in missing:
                    df[c] = pd.NA

                # Reorder: first all max_cols, then any extras in their original order
                new_order = max_cols + [c for c in cur_cols if c in extra]
                df = df[new_order]

                # Normalize Start Date (to YYYY-MM-DD strings)
                if 'Start Date' in df.columns:
                    df['Start Date'] = (
                        pd.to_datetime(
                            df['Start Date'],
                            dayfirst=True,
                            format = 'mixed'
                        )
                    )
                    df["Start Date"] = df["Start Date"].dt.normalize().dt.strftime("%Y-%m-%d")

                df.to_csv(path, index=False)
                break


def drop_unnamed_columns(players_dir=PLAYERS_DIR):
    """Remove the blank spacer columns Statsguru tables contain."""
    root_dir = players_dir
    suffixes = FILE_SUFFIXES

    for dirpath, _, filenames in os.walk(root_dir):
        for fname in filenames:
            if any(fname.endswith(suf) for suf in suffixes):
                path = os.path.join(dirpath, fname)
                try:
                    df = pd.read_csv(path)
                except Exception:
                    continue

                # Drop any column whose name starts with "Unnamed"
                df = df.loc[:, ~df.columns.str.startswith('Unnamed')]

                df.to_csv(path, index=False)
