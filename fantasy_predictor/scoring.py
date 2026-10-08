"""Stage 1d: Dream11 T20 fantasy points for every scraped innings.

The row-level rules (``batting_points``, ``bowling_points`` and the fielding
columns) are kept separate from the file handling so they can be unit tested.
"""
import os

import numpy as np
import pandas as pd

from .config import PLAYERS_DIR


def out_value(val):
    """1 if the batter was dismissed, 0 if not out, NaN if they did not bat."""
    if val == 'DNB':
        return np.nan
    elif val.endswith('*'):
        return 0
    else:
        return 1


def batting_points(row):
    """Fantasy points for one batting innings (needs Runs, BF, SR, 4s, 6s, out)."""
    runs     = row['Runs']
    bf       = row['BF']
    sr       = row['SR']
    fours    = row['4s']
    sixes    = row['6s']
    is_out   = row['out']  # 1 if out, 0 if not out

    points = 0

    # 1) Runs => +1 point per run
    points += runs

    # 2) Boundary Bonuses
    points += fours * 4
    points += sixes * 6

    # 3) Run-based Bonus (take the highest bracket only)
    if runs >= 100:
        points += 16
    elif runs >= 75:
        points += 12
    elif runs >= 50:
        points += 8
    elif runs >= 25:
        points += 4

    # 4) Dismissal for a Duck => -2
    if runs == 0 and is_out == 1:
        points -= 2

    # 5) Strike Rate bonus/penalty (min 10 balls played)
    if bf > 10:
        if sr > 170:
            points += 6
        elif sr > 150:
            points += 4
        elif sr >= 130:
            points += 2
        elif sr >= 70:
            pass  # No change
        elif sr >= 60:
            points -= 2
        elif sr >= 50:
            points -= 4
        else:
            points -= 6

    return 0 if pd.isna(points) or points is None else points


def bowling_points(row, wickets_df):
    """Fantasy points for one bowling innings.

    row        : a row of the bowler's innings table
    wickets_df : the bowler's dismissals in that same match
    """
    overs = row['Overs']
    mdns  = row['Mdns']
    econ  = row['Econ']

    # Filter out run outs => we only want "true" bowling wickets
    valid_modes = ['lbw', 'bowled', 'caught']
    valid_wickets = wickets_df[wickets_df['How out'].str.lower().isin(valid_modes)]
    total_wickets = len(valid_wickets)

    # Count LBW or Bowled dismissals
    lbw_bowled_wickets = valid_wickets[
        valid_wickets['How out'].str.lower().isin(['lbw','bowled'])
    ]
    lbw_bowled_count = lbw_bowled_wickets.shape[0]

    points = 0

    # Wickets => +30 each (excluding run out)
    points += total_wickets * 30

    # Bonus for LBW/Bowled => +8 each
    points += lbw_bowled_count * 8

    # 3/4/5 Wicket Bonus => highest bracket only
    if total_wickets >= 5:
        points += 12
    elif total_wickets >= 4:
        points += 8
    elif total_wickets >= 3:
        points += 4

    # Maiden Overs => +12 each
    points += mdns * 12

    # Economy Rate Bonus/Penalty (min 2 overs)
    if overs >= 2:
        if econ < 5:
            points += 6
        elif econ < 6:
            points += 4
        elif econ <= 7:
            points += 2
        elif econ < 10:
            pass  # 0 points
        elif econ <= 11:
            points -= 2
        elif econ <= 12:
            points -= 4
        else:
            points -= 6

    # Dot balls are not in the scorecard, so estimate them from runs conceded (capped at 24)
    mdns_dots = (0 if pd.isna(row['Mdns']) else row['Mdns']) * 6
    balls1 = (0 if pd.isna(overs) else overs) * 6
    remaining_balls = balls1 - mdns_dots
    extras_estimate = (0 if pd.isna(row['Runs']) else row['Runs']) / 5 + (0 if pd.isna(row['Runs']) else row['Runs']) / 3
    dots_from_remaining = remaining_balls - extras_estimate
    total_dots = mdns_dots + dots_from_remaining
    points += max(0, min(24,(round(total_dots))))

    return 0 if pd.isna(points) or points is None else points


def process_fantasy_points_bat(file_path):
    """Add an 'out' flag and FantasyPoints to a batting innings file, in place."""
    df = pd.read_csv(file_path)

    required_columns = [
        'Runs', 'Mins', 'BF', '4s', '6s', 'SR', 'Pos', 'Dismissal',
        'Inns', 'Unnamed: 9', 'Opposition', 'Ground', 'Start Date',
        'Unnamed: 13'
    ]

    # Check if all required columns are in the DataFrame
    missing_columns = set(required_columns) - set(df.columns)

    if missing_columns:
        required_columns.extend(['Ground Link',	'Team Link', 'out', 'FantasyPoints'])
        empty_df = pd.DataFrame(columns=required_columns)
        empty_df.to_csv(file_path, index=False)
        return

    # Convert 'Runs' column to string and filter out 'TDNB' entries
    df['Runs'] = df['Runs'].astype(str)
    df = df[df['Runs'] != 'TDNB']

    df['out'] = df['Runs'].apply(out_value)
    df['out'] = df['out'].fillna(-1).astype(int)
    df['out'] = df['out'].replace(-1, np.nan)

    df['Runs'] = df['Runs'].astype(str).str.extract(r'(\d+)')[0].astype(float)

    # Convert relevant columns to numeric
    numeric_cols = ['Runs', 'BF', 'SR', '4s', '6s', 'out']
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    df['FantasyPoints'] = df.apply(batting_points, axis=1)
    df.to_csv(file_path, index=False)


def process_fantasy_points_bowl(file_path, wickets_file_path):
    """Add match_id and FantasyPoints to a bowling innings file, in place.

    file_path         : the bowler's innings file
    wickets_file_path : the bowler's dismissal list, used to count wicket types
    """
    df = pd.read_csv(file_path)
    df1 = pd.read_csv(wickets_file_path)

    required_columns_df = [
        'Overs', 'Mdns', 'Runs', 'Wkts', 'Econ','Opposition', 'Ground', 'Start Date', 'Ground Link', 'Team Link'
    ]
    missing_columns_df = set(required_columns_df) - set(df.columns)

    required_columns_df1 = [
        'Batter', 'How out', 'Fielder', 'Runs', 'Inns','Opposition', 'Ground', 'Start Date', 'Ground Link', 'Team Link'
    ]
    missing_columns_df1 = set(required_columns_df1) - set(df1.columns)

    if missing_columns_df or missing_columns_df1:
        save_cols=["Overs", "Mdns", "Runs", "Wkts", "Econ", "Pos", "Inns", "Unnamed: 7",
                   "Opposition", "Ground", "Start Date", "Unnamed: 11",'Ground Link', 'Team Link', "match_id", "FantasyPoints"]
        empty_df = pd.DataFrame(columns=save_cols)
        empty_df.to_csv(file_path, index=False)
        return

    # Ensure numeric columns are converted properly
    df['Overs'] = df['Overs'].astype(str)
    df = df[df['Overs'] != 'TDNB']

    numeric_cols = ['Overs', 'Mdns', 'Runs', 'Wkts', 'Econ']
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # Create a match identifier column
    df['match_id'] = df[['Opposition', 'Ground', 'Start Date']].astype(str).agg('-'.join, axis=1)
    df1['match_id'] = df1[['Opposition', 'Ground', 'Start Date']].astype(str).agg('-'.join, axis=1)

    # Group wickets data by match ID
    df1_groups = df1.groupby('match_id')

    def get_bowling_points(row):
        mid = row['match_id']
        if mid in df1_groups.groups:
            wickets_data = df1_groups.get_group(mid)
        else:
            # No wickets recorded for this match in df1
            wickets_data = pd.DataFrame(columns=df1.columns)
        return bowling_points(row, wickets_data)

    df['FantasyPoints'] = df.apply(get_bowling_points, axis=1)
    df.to_csv(file_path, index=False)


def process_fantasy_points_field(file_path):
    """Add fielding FantasyPoints to a fielding innings file, in place.

    - Catch: +8 pts
    - 3 Catch Bonus: +4 pts
    - Stumping: +12 pts
    """
    df = pd.read_csv(file_path)

    # Ensure required columns exist
    required_columns = ['Dis', 'Ct', 'St', "Ct Wk", "Ct Fi", "Inns", "Opposition", "Ground", "Start Date"]
    missing_columns = set(required_columns) - set(df.columns)

    if missing_columns:
        save_cols = ["Dis", "Ct", "St", "Ct Wk", "Ct Fi", "Inns", "Unnamed: 6", "Opposition", "Ground", "Start Date", "Unnamed: 10",'Ground Link', 'Team Link',
                    "Catch Points", "Catch Bonus", "Stumping Points", "FantasyPoints"]

        df = pd.DataFrame(columns=save_cols)
        df.to_csv(file_path, index=False)
        return

    df['Dis'] = df['Dis'].astype(str)
    df = df[df['Dis'] != 'TDNF']

    # Convert to numeric to avoid issues with strings or NaN values
    df[['Ct', 'St']] = df[['Ct', 'St']].apply(pd.to_numeric, errors='coerce').fillna(0)

    # Calculate fielding points
    df['Catch Points'] = df['Ct'] * 8  # Each catch = 8 points
    df['Catch Bonus'] = (df['Ct'] // 3) * 4  # Every 3 catches = 4 bonus points
    df['Stumping Points'] = df['St'] * 12  # Each stumping = 12 points

    # Total fielding points
    df['FantasyPoints'] = df[['Catch Points', 'Catch Bonus', 'Stumping Points']].sum(axis=1).fillna(0)

    df.to_csv(file_path, index=False)


def score_all_player_files(players_dir=PLAYERS_DIR):
    """Score every batting, bowling and fielding file under ``players_dir``."""
    base_dir = players_dir
    for player_folder in os.listdir(base_dir):  # Loop over player folders
        if os.path.isdir(f"{base_dir}/{player_folder}"):  # Ensure it's a directory
            for file in os.listdir(f"{base_dir}/{player_folder}"):  # Loop over files in the folder
                if file.endswith("_bat.csv"):
                    process_fantasy_points_bat(f"{base_dir}/{player_folder}/{file}")
                elif file.endswith("_bowl.csv"):
                    process_fantasy_points_bowl(f"{base_dir}/{player_folder}/{file}",f"{base_dir}/{player_folder}/{file[:-4]}_wic.csv")
                elif file.endswith("_field.csv"):
                    process_fantasy_points_field(f"{base_dir}/{player_folder}/{file}")
