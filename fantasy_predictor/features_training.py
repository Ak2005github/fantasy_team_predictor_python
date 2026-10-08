"""Stage 1i: per-innings training features (form before each innings, plus venue history).

Each feature row only uses innings strictly before it (``shift(1)``), so the
models are trained without looking ahead.
"""
import os

import numpy as np
import pandas as pd

from .config import MERGED_BAT_CSV, MERGED_BOWL_CSV, MERGED_COMBINED_CSV, PLAYERS_DIR
from .cricket import convert_overs_to_balls


# --------------------------------------------------------------------------- batting
def batting_venue_history(df):
    """For each innings, the batter's record at that ground in earlier innings."""
    ground_features = []
    past_rows = []

    for i in range(len(df)):
        row = df.iloc[i]
        ground = row['Ground']
        match_date = row['Start Date']

        ground_history = pd.DataFrame(past_rows, columns=df.columns)
        ground_history = ground_history[
            (ground_history['Ground'] == ground) &
            (ground_history['Start Date'] < match_date)
        ]

        ground_features_row = {}

        if not ground_history.empty:
            for w in [2, 3, 5]:
                hist = ground_history.sort_values(by='Start Date').tail(w).copy()
                hist[['Runs', 'BF', '4s', '6s', 'FantasyPoints']] = hist[['Runs', 'BF', '4s', '6s', 'FantasyPoints']].fillna(0)

                hist['Boundaries'] = hist['4s'] + hist['6s']
                hist['SR'] = (hist['Runs'] / hist['BF']) * 100
                hist.loc[hist['BF'] <= 10, 'SR'] = 0

                for metric in ['Runs', '4s', '6s', 'Boundaries', 'FantasyPoints', 'SR']:
                    ground_features_row[f'Ak_Ground_Mean_{metric}_{w}'] = hist[metric].mean()
                    ground_features_row[f'Ak_Ground_Std_{metric}_{w}'] = hist[metric].std()
                    if metric == '4s' or metric == '6s' or metric == 'Boundaries':
                        ground_features_row[f'Ak_Ground_Sum_{metric}_{w}'] = hist[metric].sum()

                bf_sum = hist['BF'].sum()
                bd_sum = hist['Boundaries'].sum()
                ground_features_row[f'Ak_Ground_Boundary_Ratio_{w}'] = (bd_sum / bf_sum * 100) if bf_sum else 0

            # SR Ratio features
            runs_shifted = ground_history['Runs']
            bf_shifted = ground_history['BF']
            runs_masked = runs_shifted.where(bf_shifted > 10, 0)
            bf_masked = bf_shifted.where(bf_shifted > 10, 0)

            for w in [2, 3, 5]:
                runs_sum = runs_masked.tail(w).sum()
                bf_sum = bf_masked.tail(w).sum()
                if bf_sum==0:
                    sr_ratio=0
                else:
                    sr_ratio = (runs_sum / bf_sum * 100)
                if np.isnan(sr_ratio):
                    sr_ratio = 0
                ground_features_row[f'Ak_Ground_SR_ratio_{w}'] = sr_ratio if not np.isnan(sr_ratio) else 0

            # Perc_Run_gt_X features
            for threshold in range(10, 101, 10):
                perc_series = (ground_history['Runs'] > threshold).tail(5).mean() * 100
                ground_features_row[f'Ak_Ground_Perc_Run_gt_{threshold}_5'] = perc_series if not np.isnan(perc_series) else 0

        else:
            # Fill with zeros if no prior ground data
            for w in [2, 3, 5]:
                for metric in ['Runs', '4s', '6s', 'Boundaries', 'FantasyPoints', 'SR']:
                    ground_features_row[f'Ak_Ground_Mean_{metric}_{w}'] = 0
                    ground_features_row[f'Ak_Ground_Std_{metric}_{w}'] = 0
                    if metric == '4s' or metric == '6s' or metric == 'Boundaries':
                        ground_features_row[f'Ak_Ground_Sum_{metric}_{w}'] = 0
                ground_features_row[f'Ak_Ground_Boundary_Ratio_{w}'] = 0
                ground_features_row[f'Ak_Ground_SR_ratio_{w}'] = 0

            for threshold in range(10, 101, 10):
                ground_features_row[f'Ak_Ground_Perc_Run_gt_{threshold}_5'] = 0

        ground_features.append(ground_features_row)
        past_rows.append(row.to_dict())

    return pd.DataFrame(ground_features)


def batting_training_features(filepath, cut_date):
    """Rolling batting form (windows 2-5) plus venue history for each innings before ``cut_date``."""
    df = pd.read_csv(filepath)
    df.columns = df.columns.str.strip()

    required = {'Start Date', 'Runs', 'BF', 'Ground'}
    if not required.issubset(df.columns):
        return None

    # Convert and filter dates
    df['Start Date'] = pd.to_datetime(df['Start Date'], errors='coerce')
    df = df[df['Start Date'] < cut_date]
    df_2023 = df[df['Start Date'].dt.year >= 2023][['Start Date','Ground', 'Inns', 'Runs','BF', 'FantasyPoints', '4s', '6s']].copy()
    df[['Runs', 'BF', '4s', '6s']] = df[['Runs', 'BF', '4s', '6s']].fillna(0)
    df_2023["Runs"] = df_2023['Runs'].fillna(0)
    df_2023['4s'] = df_2023['4s'].fillna(0)
    df_2023['6s'] = df_2023['6s'].fillna(0)

    # Window sizes for rolling calculations
    windows = [2, 3, 4, 5]
    boundary_windows = [2, 4,6]

    # Calculate rolling features for Runs (shifted)
    for window in windows:
        df_2023[f'Mean_Run_{window}'] = df_2023['Runs'].shift(1).rolling(window).mean()
        df_2023[f'Std_Run_{window}'] = df_2023['Runs'].shift(1).rolling(window).std()

    # Calculate rolling features for FantasyPoints (shifted)
    for window in windows:
        df_2023[f'Mean_Fan_{window}'] = df_2023['FantasyPoints'].shift(1).rolling(window).mean()
        df_2023[f'Std_Fan_{window}'] = df_2023['FantasyPoints'].shift(1).rolling(window).std()

    # Calculate rolling features for 4s and 6s (shifted)
    for window in boundary_windows:
        # Features for 4s
        df_2023[f'Mean_4s_{window}'] = df_2023['4s'].shift(1).rolling(window).mean()
        df_2023[f'Std_4s_{window}'] = df_2023['4s'].shift(1).rolling(window).std()
        df_2023[f'Sum_4s_{window}'] = df_2023['4s'].shift(1).rolling(window).sum()

        # Features for 6s
        df_2023[f'Mean_6s_{window}'] = df_2023['6s'].shift(1).rolling(window).mean()
        df_2023[f'Std_6s_{window}'] = df_2023['6s'].shift(1).rolling(window).std()
        df_2023[f'Sum_6s_{window}'] = df_2023['6s'].shift(1).rolling(window).sum()

        # Combined boundaries (4s + 6s)
        df_2023[f'Mean_Boundaries_{window}'] = (df_2023['4s'] + df_2023['6s']).shift(1).rolling(window).mean()
        df_2023[f'Std_Boundaries_{window}'] = (df_2023['4s'] + df_2023['6s']).shift(1).rolling(window).std()
        df_2023[f'Sum_Boundaries_{window}'] = (df_2023['4s'] + df_2023['6s']).shift(1).rolling(window).sum()

        # Boundary ratio (boundaries per ball faced)
        boundaries_shifted = (df_2023['4s'] + df_2023['6s']).shift(1)
        bf_shifted = df_2023['BF'].shift(1)
        df_2023[f'Boundary_Ratio_{window}'] = (
            boundaries_shifted.rolling(window).sum() /
            bf_shifted.rolling(window).sum() * 100
        ).fillna(0)

    runs_shifted = df_2023['Runs'].shift(1)
    # thresholds 10,20,...,100
    for threshold in range(10, 101, 10):
        df_2023[f'Perc_Run_gt_{threshold}_10'] = (
            (runs_shifted > threshold)
            .rolling(5)
            .mean()
            * 100
        )
    for w in [3, 5]:
        df_2023[f'Median_Run_{w}'] = df_2023['Runs'].shift(1).rolling(w).median()
    df_2023['BF'] = df_2023['BF'].fillna(0)
    # compute masked strike rate (%)
    df_2023['SR1'] = df_2023['Runs'] / df_2023['BF'] * 100
    df_2023.loc[df_2023['BF'] <= 10, 'SR1'] = 0
    # rolling-mean SR over previous 3 and 5 matches
    for w in [3, 5]:
        df_2023[f'Mean_SR_{w}'] = (
            df_2023['SR1']
            .shift(1)              # exclude current match
            .rolling(w)
            .mean()
        )
        df_2023[f'Std_SR_{w}'] = (
            df_2023['SR1']
            .shift(1)              # exclude current match
            .rolling(w)
            .std()
        )
    # drop the helper SR column
    df_2023.drop(columns=['SR1'], inplace=True)
    # shift so current match isn't included
    runs_shifted = df_2023['Runs'].shift(1)
    bf_shifted   = df_2023['BF'].shift(1)
    # zero-out any innings with BF <= 10
    runs_masked = runs_shifted.where(bf_shifted > 10, 0)
    bf_masked   = bf_shifted.where(bf_shifted > 10,   0)
    for w in [3, 5]:
        # sum only the valid runs and balls over the window
        runs_sum = runs_masked.rolling(w).sum()
        bf_sum   = bf_masked.rolling(w).sum()
        # compute SR%; if bf_sum is 0, set SR to 0
        df_2023[f'SR_ratio_{w}'] = np.where(bf_sum == 0, 0, (runs_sum / bf_sum * 100).fillna(0))

    # Drop rows with NaN values (from shifting and rolling windows)
    df= df_2023.dropna()
    venue_features_df = batting_venue_history(df)
    return pd.concat([df.reset_index(drop=True), venue_features_df], axis=1)


# --------------------------------------------------------------------------- bowling
def bowling_venue_history(df):
    """For each innings, the bowler's record at that ground in earlier innings."""
    ground_features = []
    past_rows = []

    for i in range(len(df)):
        row = df.iloc[i]
        ground = row['Ground']
        match_date = row['Start Date']

        ground_history = pd.DataFrame(past_rows, columns=df.columns)
        ground_history = ground_history[
            (ground_history['Ground'] == ground) &
            (ground_history['Start Date'] < match_date)
        ]

        ground_row = {}

        if not ground_history.empty:
            for w in [2, 3, 5]:
                hist = ground_history.sort_values('Start Date').tail(w).copy()
                for col in ['Runs', 'Wkts', 'Econ', 'FantasyPoints', 'Balls']:
                    ground_row[f'Ak_Ground_Mean_{col}_{w}'] = hist[col].mean()
                    ground_row[f'Ak_Ground_Std_{col}_{w}'] = hist[col].std()

                ground_row[f'Ak_Ground_Sum_Balls_{w}'] = hist['Balls'].sum()
                ground_row[f'Ak_Ground_Sum_Wkts_{w}'] = hist['Wkts'].sum()

                runs_sum = hist['Runs'].sum()
                wkts_sum = hist['Wkts'].sum()
                balls_sum = hist['Balls'].sum()
                fan_sum = hist['FantasyPoints'].sum()

                ground_row[f'Ak_Ground_Weighted_Econ_{w}'] = (runs_sum / (balls_sum / 6)) if balls_sum > 0 else 0
                ground_row[f'Ak_Ground_Wkt_Rate_{w}'] = (wkts_sum / (balls_sum / 6)) if balls_sum > 0 else 0
                ground_row[f'Ak_Ground_Fan_Efficiency_{w}'] = (fan_sum / balls_sum) if balls_sum > 0 else 0
                ground_row[f'Ak_Ground_Strike_Rate_{w}'] = (balls_sum / wkts_sum) if wkts_sum > 0 else 0

            hist = ground_history.sort_values('Start Date').tail(5).copy()
            for threshold in range(10, 101, 10):
                run_cond = hist['Runs'] > threshold
                ground_row[f'Ak_Ground_Perc_Run_gt_{threshold}_5'] = run_cond.mean() * 100 if len(run_cond) >= 5 else 0

            for threshold in [1, 2, 3, 4, 5]:
                wkt_cond = hist['Wkts'] >= threshold
                ground_row[f'Ak_Ground_Perc_Wkts_gt_{threshold}_5'] = wkt_cond.mean() * 100 if len(wkt_cond) >= 5 else 0

        else:
            for w in [2, 3, 5]:
                for col in ['Runs', 'Wkts', 'Econ', 'FantasyPoints', 'Balls']:
                    ground_row[f'Ak_Ground_Mean_{col}_{w}'] = 0
                    ground_row[f'Ak_Ground_Std_{col}_{w}'] = 0
                ground_row[f'Ak_Ground_Sum_Balls_{w}'] = 0
                ground_row[f'Ak_Ground_Sum_Wkts_{w}'] = 0

                ground_row[f'Ak_Ground_Weighted_Econ_{w}'] = 0
                ground_row[f'Ak_Ground_Wkt_Rate_{w}'] = 0
                ground_row[f'Ak_Ground_Fan_Efficiency_{w}'] = 0
                ground_row[f'Ak_Ground_Strike_Rate_{w}'] = 0

            for threshold in range(10, 101, 10):
                ground_row[f'Ak_Ground_Perc_Run_gt_{threshold}_5'] = 0
            for threshold in [1, 2, 3, 4, 5]:
                ground_row[f'Ak_Ground_Perc_Wkts_gt_{threshold}_5'] = 0

        ground_features.append(ground_row)
        past_rows.append(row.to_dict())

    return pd.DataFrame(ground_features)


def _bowling_form(df_2023):
    """Rolling bowling form shared by the bowling and all-rounder training tables."""
    # Global features
    for window in [2, 3, 4, 5, 6]:
        df_2023[f'Mean_Run_{window}'] = df_2023['Runs'].shift(1).rolling(window).mean()
        df_2023[f'Std_Run_{window}'] = df_2023['Runs'].shift(1).rolling(window).std()
        df_2023[f'Mean_Fan_{window}'] = df_2023['FantasyPoints'].shift(1).rolling(window).mean()
        df_2023[f'Std_Fan_{window}'] = df_2023['FantasyPoints'].shift(1).rolling(window).std()

    for window in [2, 4, 6]:
        df_2023[f'Mean_Wkts_{window}'] = df_2023['Wkts'].shift(1).rolling(window).mean()
        df_2023[f'Std_Wkts_{window}'] = df_2023['Wkts'].shift(1).rolling(window).std()

    for threshold in range(10, 101, 10):
        df_2023[f'Perc_Run_gt_{threshold}_10'] = (df_2023['Runs'].shift(1) > threshold).rolling(5).mean() * 100

    for threshold in [1, 2, 3, 4, 5]:
        df_2023[f'Perc_Wkts_gt_{threshold}_10'] = (df_2023['Wkts'].shift(1) >= threshold).rolling(5).mean() * 100

    for w in [3, 5]:
        df_2023[f'Median_Run_{w}'] = df_2023['Runs'].shift(1).rolling(w).median()
        df_2023[f'Median_Wkts_{w}'] = df_2023['Wkts'].shift(1).rolling(w).median()
        df_2023[f'Mean_Econ_{w}'] = df_2023['Econ'].shift(1).rolling(w).mean()
        df_2023[f'Std_Econ_{w}'] = df_2023['Econ'].shift(1).rolling(w).std()
        df_2023[f'Sum_Balls_{w}'] = df_2023['Balls'].shift(1).rolling(w).sum()
        df_2023[f'Sum_Wkts_{w}'] = df_2023['Wkts'].shift(1).rolling(w).sum()

        runs_sum = df_2023['Runs'].shift(1).rolling(w).sum()
        balls_sum = df_2023['Balls'].shift(1).rolling(w).sum().replace(0, np.nan)
        wkts_sum = df_2023['Wkts'].shift(1).rolling(w).sum().replace(0, np.nan)
        fan_sum = df_2023['FantasyPoints'].shift(1).rolling(w).sum()

        df_2023[f'Weighted_Econ_{w}'] = (runs_sum / (balls_sum / 6)).fillna(0)
        df_2023[f'Wkt_Rate_{w}'] = (wkts_sum / (balls_sum / 6)).fillna(0)
        df_2023[f'Fan_Efficiency_{w}'] = (fan_sum / balls_sum).fillna(0)
        df_2023[f'Strike_Rate_{w}'] = (balls_sum / wkts_sum).fillna(0)

    df_2023 = df_2023.rename(columns={'Inns': 'BowlInns'})
    df_2023 = df_2023.reset_index(drop=True)
    return df_2023


def _bowling_innings_since_2023(file_path, cut_date):
    df = pd.read_csv(file_path)
    df.columns = df.columns.str.strip()

    required_columns = {'Start Date', 'Overs', 'Mdns', 'Inns', 'Runs', 'Econ', 'FantasyPoints'}
    if not required_columns.issubset(df.columns):
        return None

    df['Start Date'] = pd.to_datetime(df['Start Date'], errors='coerce')
    df = df[df['Start Date'] < cut_date]
    df_2023 = df[df['Start Date'].dt.year >= 2023].copy()

    df_2023['Balls'] = df_2023['Overs'].apply(convert_overs_to_balls)
    df_2023[['Runs', 'Wkts']] = df_2023[['Runs', 'Wkts']].fillna(0)
    df_2023 = df_2023.sort_values('Start Date').reset_index(drop=True)
    return df_2023


def bowling_training_features(file_path, cut_date):
    """Rolling bowling form plus venue history for each innings before ``cut_date``."""
    df_2023 = _bowling_innings_since_2023(file_path, cut_date)
    if df_2023 is None:
        return None
    df_2023 = _bowling_form(df_2023)
    venue_features_df = bowling_venue_history(df_2023)
    return pd.concat([df_2023, venue_features_df], axis=1).reset_index(drop=True)


# --------------------------------------------------------------------------- all-rounders
def allrounder_bowling_training_features(file_path, cut_date):
    """Rolling bowling form only (no venue history), for the all-rounder table."""
    df_2023 = _bowling_innings_since_2023(file_path, cut_date)
    if df_2023 is None:
        return None
    return _bowling_form(df_2023)


def allrounder_batting_training_features(filepath, cut_date):
    """Rolling batting form (windows 2-6, no venue history), for the all-rounder table."""
    df = pd.read_csv(filepath)
    df.columns = df.columns.str.strip()

    required = {'Start Date', 'Runs', 'BF', 'Ground'}
    if not required.issubset(df.columns):
        return None

    df['Start Date'] = pd.to_datetime(df['Start Date'], errors='coerce')
    df = df[df['Start Date'] < cut_date]
    df_2023 = df[df['Start Date'].dt.year >= 2023][['Start Date','Ground', 'Inns', 'Runs','BF', 'FantasyPoints', '4s', '6s']].copy()
    df[['Runs', 'BF', '4s', '6s']] = df[['Runs', 'BF', '4s', '6s']].fillna(0)
    df_2023["Runs"] = df_2023['Runs'].fillna(0)
    df_2023['4s'] = df_2023['4s'].fillna(0)
    df_2023['6s'] = df_2023['6s'].fillna(0)

    # Window sizes for rolling calculations
    windows = [2, 3, 4, 5, 6]
    boundary_windows = [2, 4, 6]

    for window in windows:
        df_2023[f'Mean_Run_{window}'] = df_2023['Runs'].shift(1).rolling(window).mean()
        df_2023[f'Std_Run_{window}'] = df_2023['Runs'].shift(1).rolling(window).std()

    for window in windows:
        df_2023[f'Mean_Fan_{window}'] = df_2023['FantasyPoints'].shift(1).rolling(window).mean()
        df_2023[f'Std_Fan_{window}'] = df_2023['FantasyPoints'].shift(1).rolling(window).std()

    for window in boundary_windows:
        df_2023[f'Mean_4s_{window}'] = df_2023['4s'].shift(1).rolling(window).mean()
        df_2023[f'Std_4s_{window}'] = df_2023['4s'].shift(1).rolling(window).std()
        df_2023[f'Sum_4s_{window}'] = df_2023['4s'].shift(1).rolling(window).sum()

        df_2023[f'Mean_6s_{window}'] = df_2023['6s'].shift(1).rolling(window).mean()
        df_2023[f'Std_6s_{window}'] = df_2023['6s'].shift(1).rolling(window).std()
        df_2023[f'Sum_6s_{window}'] = df_2023['6s'].shift(1).rolling(window).sum()

        df_2023[f'Mean_Boundaries_{window}'] = (df_2023['4s'] + df_2023['6s']).shift(1).rolling(window).mean()
        df_2023[f'Std_Boundaries_{window}'] = (df_2023['4s'] + df_2023['6s']).shift(1).rolling(window).std()
        df_2023[f'Sum_Boundaries_{window}'] = (df_2023['4s'] + df_2023['6s']).shift(1).rolling(window).sum()

        boundaries_shifted = (df_2023['4s'] + df_2023['6s']).shift(1)
        bf_shifted = df_2023['BF'].shift(1)
        df_2023[f'Boundary_Ratio_{window}'] = (
            boundaries_shifted.rolling(window).sum() /
            bf_shifted.rolling(window).sum() * 100
        ).fillna(0)

    runs_shifted = df_2023['Runs'].shift(1)
    for threshold in range(10, 101, 10):
        df_2023[f'Perc_Run_gt_{threshold}_10'] = (
            (runs_shifted > threshold)
            .rolling(5)
            .mean()
            * 100
        )
    for w in [3, 5]:
        df_2023[f'Median_Run_{w}'] = df_2023['Runs'].shift(1).rolling(w).median()
    df_2023['BF'] = df_2023['BF'].fillna(0)
    df_2023['SR1'] = df_2023['Runs'] / df_2023['BF'] * 100
    df_2023.loc[df_2023['BF'] <= 10, 'SR1'] = 0
    for w in [3, 5]:
        df_2023[f'Mean_SR_{w}'] = df_2023['SR1'].shift(1).rolling(w).mean()
        df_2023[f'Std_SR_{w}'] = df_2023['SR1'].shift(1).rolling(w).std()
    df_2023.drop(columns=['SR1'], inplace=True)
    runs_shifted = df_2023['Runs'].shift(1)
    bf_shifted   = df_2023['BF'].shift(1)
    runs_masked = runs_shifted.where(bf_shifted > 10, 0)
    bf_masked   = bf_shifted.where(bf_shifted > 10,   0)
    for w in [3, 5]:
        runs_sum = runs_masked.rolling(w).sum()
        bf_sum   = bf_masked.rolling(w).sum()
        df_2023[f'SR_ratio_{w}'] = (runs_sum / bf_sum * 100).fillna(0)
    df= df_2023.dropna()
    return df.reset_index(drop=True)


# --------------------------------------------------------------------------- writing tables
def _write_player_features(players_dir, ftype, build, cut_date):
    """Run ``build`` on every player's ``<id>_<ftype>.csv`` and save ``<id>features<ftype>.csv``."""
    for player_folder in os.listdir(players_dir):
        player_path = os.path.join(players_dir, player_folder)
        if os.path.isdir(player_path):
            filename = f"{player_folder}_{ftype}.csv"
            filepath = os.path.join(player_path, filename)
            if os.path.exists(filepath):
                result_df = build(filepath, cut_date)
                if result_df is not None:
                    out_path = os.path.join(player_path, f"{player_folder}features{ftype}.csv")
                    result_df.to_csv(out_path, index=False)


def _collect_player_features(players_dir, ftype):
    dfs = []
    for player_folder in os.listdir(players_dir):
        player_path = os.path.join(players_dir, player_folder)
        if os.path.isdir(player_path):
            file_path = os.path.join(player_path, f"{player_folder}features{ftype}.csv")
            if os.path.exists(file_path):
                df = pd.read_csv(file_path)
                df['PlayerID'] = player_folder
                dfs.append(df)
    return dfs


def _round_numeric(merged):
    for col in merged.select_dtypes(include='number').columns:
        merged[col] = merged[col].astype(float).round(1)
    return merged


def build_batting_training_table(cut_date, players_dir=PLAYERS_DIR, out_csv=MERGED_BAT_CSV):
    _write_player_features(players_dir, 'bat', batting_training_features, cut_date)
    df_list = _collect_player_features(players_dir, 'bat')
    if df_list:
        # Exclude empty or all-NA DataFrames from the list
        clean_df_list = [df for df in df_list if not df.empty and not df.isna().all().all()]
        merged = _round_numeric(pd.concat(clean_df_list, ignore_index=True))
        merged.to_csv(out_csv, index=False)


def build_bowling_training_table(cut_date, players_dir=PLAYERS_DIR, out_csv=MERGED_BOWL_CSV):
    _write_player_features(players_dir, 'bowl', bowling_training_features, cut_date)
    df_list = _collect_player_features(players_dir, 'bowl')
    if df_list:
        # Drop all-NaN columns in each df before merging to avoid FutureWarning
        cleaned_dfs = [df.dropna(axis=1, how='all') for df in df_list if not df.empty]
        if cleaned_dfs:
            merged = _round_numeric(pd.concat(cleaned_dfs, ignore_index=True))
            merged.to_csv(out_csv, index=False)


def build_allrounder_training_table(cut_date, players_dir=PLAYERS_DIR, out_csv=MERGED_COMBINED_CSV):
    """Join batting and bowling form by date and ground for players who have both."""
    base_dir = players_dir
    players_with_both_data = set()
    players_with_bat_data = set()
    players_with_bowl_data = set()

    # First pass: identify players with both types of data
    for player_folder in os.listdir(base_dir):
        player_path = os.path.join(base_dir, player_folder)
        if os.path.isdir(player_path):
            has_bat_data = os.path.exists(os.path.join(player_path, f"{player_folder}_bat.csv"))
            has_bowl_data = os.path.exists(os.path.join(player_path, f"{player_folder}_bowl.csv"))

            if has_bat_data:
                players_with_bat_data.add(player_folder)
            if has_bowl_data:
                players_with_bowl_data.add(player_folder)
            if has_bat_data and has_bowl_data:
                players_with_both_data.add(player_folder)

    # Second pass: process and merge data for players with both types
    for player_folder in players_with_both_data:
        player_path = os.path.join(base_dir, player_folder)

        bat_df = allrounder_batting_training_features(os.path.join(player_path, f"{player_folder}_bat.csv"), cut_date)
        bowl_df = allrounder_bowling_training_features(os.path.join(player_path, f"{player_folder}_bowl.csv"), cut_date)

        if bat_df is not None and bowl_df is not None:
            bat_df.to_csv(os.path.join(player_path, f"{player_folder}featuresbat1.csv"), index=False)
            bowl_df.to_csv(os.path.join(player_path, f"{player_folder}featuresbowl1.csv"), index=False)

            # Merge on Start Date and Ground to handle same-day matches properly
            common_cols = ['Start Date', 'Ground']

            # Prefix batting and bowling columns except the common ones
            bat_cols = [col for col in bat_df.columns if col not in common_cols]
            bat_df_prefixed = bat_df.copy()
            for col in bat_cols:
                bat_df_prefixed.rename(columns={col: f'bat_{col}'}, inplace=True)

            bowl_cols = [col for col in bowl_df.columns if col not in common_cols]
            bowl_df_prefixed = bowl_df.copy()
            for col in bowl_cols:
                bowl_df_prefixed.rename(columns={col: f'bowl_{col}'}, inplace=True)

            combined_df = pd.merge(
                bat_df_prefixed,
                bowl_df_prefixed,
                on=common_cols,
                how='outer',
                suffixes=('_bat', '_bowl')
            )

            combined_df['PlayerID'] = player_folder
            combined_df.to_csv(os.path.join(player_path, f"{player_folder}features_combined.csv"), index=False)

    # Create master merged file
    combined_dfs = []
    for player_folder in os.listdir(base_dir):
        player_path = os.path.join(base_dir, player_folder)
        if os.path.isdir(player_path) and player_folder in players_with_both_data:
            combined_path = os.path.join(player_path, f"{player_folder}features_combined.csv")
            if os.path.exists(combined_path):
                combined_dfs.append(pd.read_csv(combined_path))

    if combined_dfs:
        merged_combined = _round_numeric(pd.concat(combined_dfs, ignore_index=True))
        merged_combined.to_csv(out_csv, index=False)
