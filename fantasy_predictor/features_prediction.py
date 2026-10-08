"""Stage 2a: one feature row per player, describing current form going into the match.

These mirror the training features but summarise the latest innings
(``tail``) instead of rolling over history.
"""
import numpy as np
import pandas as pd

from .cricket import convert_overs_to_balls


def batting_venue_features(df, features, ground):
    """Add the batter's record at the match ``ground`` to ``features``."""
    ground_history = df[df['Ground'] == ground]

    if not ground_history.empty:
        for w in [2, 3, 5]:
            hist = ground_history.sort_values(by='Start Date').tail(w).copy()
            hist[['Runs', 'BF', '4s', '6s', 'FantasyPoints']] = hist[['Runs', 'BF', '4s', '6s', 'FantasyPoints']].fillna(0)

            hist['Boundaries'] = hist['4s'] + hist['6s']
            hist['SR'] = (hist['Runs'] / hist['BF']) * 100
            hist.loc[hist['BF'] <= 10, 'SR'] = 0

            for metric in ['Runs', '4s', '6s', 'Boundaries', 'FantasyPoints', 'SR']:
                features[f'Ak_Ground_Mean_{metric}_{w}'] = hist[metric].mean()
                features[f'Ak_Ground_Std_{metric}_{w}'] = hist[metric].std()
                if metric == '4s' or metric == '6s' or metric == 'Boundaries':
                    features[f'Ak_Ground_Sum_{metric}_{w}'] = hist[metric].sum()

            bf_sum = hist['BF'].sum()
            bd_sum = hist['Boundaries'].sum()
            features[f'Ak_Ground_Boundary_Ratio_{w}'] = (bd_sum / bf_sum * 100) if bf_sum else 0

        # SR Ratio features
        runs_shifted = ground_history['Runs']
        bf_shifted = ground_history['BF']
        runs_masked = runs_shifted.where(bf_shifted > 10, 0)
        bf_masked = bf_shifted.where(bf_shifted > 10, 0)

        for w in [2, 3, 5]:
            runs_sum = runs_masked.tail(w).sum()
            bf_sum = bf_masked.tail(w).sum()
            if bf_sum !=0:
                sr_ratio = (runs_sum / bf_sum * 100)
            else:
                sr_ratio=0
            if np.isnan(sr_ratio):
                sr_ratio=0
            features[f'Ak_Ground_SR_ratio_{w}'] = sr_ratio if not np.isnan(sr_ratio) else 0

        # Perc_Run_gt_X features
        for threshold in range(10, 101, 10):
            perc_series = (ground_history['Runs'] > threshold).tail(5).mean() * 100
            features[f'Ak_Ground_Perc_Run_gt_{threshold}_5'] = perc_series if not np.isnan(perc_series) else 0

    else:
        # Fill with zeros if no prior ground data
        for w in [2, 3, 5]:
            for metric in ['Runs', '4s', '6s', 'Boundaries', 'FantasyPoints', 'SR']:
                features[f'Ak_Ground_Mean_{metric}_{w}'] = 0
                features[f'Ak_Ground_Std_{metric}_{w}'] = 0
            features[f'Ak_Ground_Boundary_Ratio_{w}'] = 0
            features[f'Ak_Ground_SR_ratio_{w}'] = 0

        for threshold in range(10, 101, 10):
            features[f'Ak_Ground_Perc_Run_gt_{threshold}_5'] = 0

    return features


def batting_prediction_features(filepath, cut_date, ground):
    """Recent batting form and record at ``ground``, as a one-row DataFrame."""
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

    fours = df_2023['4s']
    sixes = df_2023['6s']
    bf = df_2023['BF']
    runs = df_2023['Runs']
    features = {}

    # Window sizes for rolling calculations
    windows = [2, 3, 4, 5, 6]
    boundary_windows = [2, 4, 6]

    for window in windows:
        features[f'Mean_Run_{window}'] = df_2023['Runs'].tail(window).mean()
        features[f'Std_Run_{window}'] = df_2023['Runs'].tail(window).std()

    for window in windows:
        features[f'Mean_Fan_{window}'] = df_2023['FantasyPoints'].tail(window).mean()
        features[f'Std_Fan_{window}'] = df_2023['FantasyPoints'].tail(window).std()

    for window in boundary_windows:
        # Features for 4s
        features[f'Mean_4s_{window}'] = df_2023['4s'].tail(window).mean()
        features[f'Std_4s_{window}'] = df_2023['4s'].tail(window).std()
        features[f'Sum_4s_{window}'] = df_2023['4s'].tail(window).sum()

        # Features for 6s
        features[f'Mean_6s_{window}'] = df_2023['6s'].tail(window).mean()
        features[f'Std_6s_{window}'] = df_2023['6s'].tail(window).std()
        features[f'Sum_6s_{window}'] = df_2023['6s'].tail(window).sum()

        # Combined boundaries (4s + 6s)
        boundaries = fours + sixes
        features[f'Mean_Boundaries_{window}'] = (df_2023['4s'] + df_2023['6s']).tail(window).mean()
        features[f'Std_Boundaries_{window}'] = (df_2023['4s'] + df_2023['6s']).tail(window).std()
        features[f'Sum_Boundaries_{window}'] = (df_2023['4s'] + df_2023['6s']).tail(window).sum()

        # Boundary ratio (boundaries per ball faced)
        if len(boundaries) >= window and len(bf) >= window:
            boundaries_sum = boundaries.tail(window).sum()
            bf_sum = bf.tail(window).sum()
            features[f'Boundary_Ratio_{window}'] = (boundaries_sum / bf_sum * 100) if bf_sum > 0 else 0
        else:
            features[f'Boundary_Ratio_{window}'] = np.nan

    for threshold in range(10, 101, 10):
        col_name = f'Perc_Run_gt_{threshold}_10'
        features[col_name] = (
            (runs > threshold).tail(5).sum() / 10.0 * 100
            if len(runs) >= 10 else np.nan
        )
    for w in [3, 5]:
        features[f'Median_Run_{w}'] = runs.tail(w).median() if len(runs) >= w else np.nan
    # Strike Rate
    sr = (runs / bf) * 100
    sr[df_2023['BF'] <= 10] = 0
    for w in [3, 5]:
        features[f'Mean_SR_{w}'] = sr.tail(w).mean() if len(sr) >= w else np.nan
        features[f'Std_SR_{w}'] = sr.tail(w).std() if len(sr) >= w else np.nan

    # Masked SR Ratio
    runs_masked = runs.where(bf > 10, 0)
    bf_masked = bf.where(bf > 10, 0)
    for w in [3, 5]:
        if len(runs_masked) >= w:
            runs_sum = runs_masked.tail(w).sum()
            bf_sum = bf_masked.tail(w).sum()
            features[f'SR_ratio_{w}'] = (runs_sum / bf_sum * 100) if bf_sum > 0 else 0
        else:
            features[f'SR_ratio_{w}'] = np.nan

    df['Start Date'] = pd.to_datetime(df['Start Date'], errors='coerce')
    df = df[df['Start Date'] < cut_date]
    df_2023 = df[df['Start Date'].dt.year >= 2023][['Start Date','Ground', 'Inns', 'Runs','BF', 'FantasyPoints', '4s', '6s']].copy()
    features = batting_venue_features(df_2023, features, ground)
    return pd.DataFrame([features])


def bowling_venue_features(features, df, ground):
    """Add the bowler's record at the match ``ground`` to ``features``."""
    ground_history = df[df['Ground']==ground]

    if not ground_history.empty:
        for w in [2, 3, 5]:
            hist = ground_history.sort_values('Start Date').tail(w).copy()
            for col in ['Runs', 'Wkts', 'Econ', 'FantasyPoints', 'Balls']:
                features[f'Ak_Ground_Mean_{col}_{w}'] = hist[col].mean()
                features[f'Ak_Ground_Std_{col}_{w}'] = hist[col].std()

            features[f'Ak_Ground_Sum_Balls_{w}'] = hist['Balls'].sum()
            features[f'Ak_Ground_Sum_Wkts_{w}'] = hist['Wkts'].sum()

            runs_sum = hist['Runs'].sum()
            wkts_sum = hist['Wkts'].sum()
            balls_sum = hist['Balls'].sum()
            fan_sum = hist['FantasyPoints'].sum()

            features[f'Ak_Ground_Weighted_Econ_{w}'] = (runs_sum / (balls_sum / 6)) if balls_sum > 0 else 0
            features[f'Ak_Ground_Wkt_Rate_{w}'] = (wkts_sum / (balls_sum / 6)) if balls_sum > 0 else 0
            features[f'Ak_Ground_Fan_Efficiency_{w}'] = (fan_sum / balls_sum) if balls_sum > 0 else 0
            features[f'Ak_Ground_Strike_Rate_{w}'] = (balls_sum / wkts_sum) if wkts_sum > 0 else 0

        hist = ground_history.sort_values('Start Date').tail(5).copy()
        for threshold in range(10, 101, 10):
            run_cond = hist['Runs'] > threshold
            features[f'Ak_Ground_Perc_Run_gt_{threshold}_5'] = run_cond.mean() * 100 if len(run_cond) >= 5 else 0

        for threshold in [1, 2, 3, 4, 5]:
            wkt_cond = hist['Wkts'] >= threshold
            features[f'Ak_Ground_Perc_Wkts_gt_{threshold}_5'] = wkt_cond.mean() * 100 if len(wkt_cond) >= 5 else 0

    else:
        for w in [2, 3, 5]:
            for col in ['Runs', 'Wkts', 'Econ', 'FantasyPoints', 'Balls']:
                features[f'Ak_Ground_Mean_{col}_{w}'] = 0
                features[f'Ak_Ground_Std_{col}_{w}'] = 0
            features[f'Ak_Ground_Sum_Balls_{w}'] = 0
            features[f'Ak_Ground_Sum_Wkts_{w}'] = 0

            features[f'Ak_Ground_Weighted_Econ_{w}'] = 0
            features[f'Ak_Ground_Wkt_Rate_{w}'] = 0
            features[f'Ak_Ground_Fan_Efficiency_{w}'] = 0
            features[f'Ak_Ground_Strike_Rate_{w}'] = 0

        for threshold in range(10, 101, 10):
            features[f'Ak_Ground_Perc_Run_gt_{threshold}_5'] = 0
        for threshold in [1, 2, 3, 4, 5]:
            features[f'Ak_Ground_Perc_Wkts_gt_{threshold}_5'] = 0

    return features


def bowling_prediction_features(file_path, cut_date, ground):
    """Bowling form over the last 10 innings and record at ``ground``, as a one-row DataFrame."""
    df = pd.read_csv(file_path)
    df.columns = df.columns.str.strip()

    required_columns = {'Start Date', 'Overs', 'Mdns', 'Inns', 'Runs', 'Econ', 'FantasyPoints'}
    if not required_columns.issubset(df.columns):
        return None

    df['Start Date'] = pd.to_datetime(df['Start Date'], errors='coerce')
    df = df.sort_values('Start Date')
    df = df[df['Start Date'] < cut_date]
    df_2023 = df[df['Start Date'].dt.year >= 2023][['Ground', 'Overs', 'Mdns', 'Inns','Wkts', 'Runs', 'Econ', 'FantasyPoints']].copy()
    df_2023 = df_2023.tail(10).copy()
    df_2023.loc[:, 'Balls'] = df_2023['Overs'].apply(convert_overs_to_balls)

    # Fill missing values for Runs conceded with 0
    df_2023['Runs'] = df_2023['Runs'].fillna(0)
    df_2023['Wkts'] = df_2023['Wkts'].fillna(0)
    features = {}
    windows = [2, 3, 4, 5, 6]
    for window in windows:
        features[f'Mean_Run_{window}'] = df_2023['Runs'].tail(window).mean()
        features[f'Std_Run_{window}'] = df_2023['Runs'].tail(window).std()
        features[f'Mean_Fan_{window}'] = df_2023['FantasyPoints'].tail(window).mean()
        features[f'Std_Fan_{window}'] = df_2023['FantasyPoints'].tail(window).std()

    for window in [2, 4, 6]:
        features[f'Mean_Wkts_{window}'] = df_2023['Wkts'].tail(window).mean()
        features[f'Std_Wkts_{window}'] = df_2023['Wkts'].tail(window).std()

    runs = df_2023['Runs']
    for threshold in range(10, 101, 10):
        features[f'Perc_Run_gt_{threshold}_10'] = (runs > threshold).tail(5).mean() * 100

    wkts_shifted = df_2023['Wkts']
    for threshold in [1, 2, 3, 4, 5]:
        features[f'Perc_Wkts_gt_{threshold}_10'] = (wkts_shifted >= threshold).tail(5).mean() * 100
    # Rolling median for Runs conceded
    for w in [3, 5]:
        features[f'Median_Run_{w}'] = df_2023['Runs'].tail(w).median()

    # Rolling median for Wickets
    for w in [3, 5]:
        features[f'Median_Wkts_{w}'] = df_2023['Wkts'].tail(w).median()

    # Rolling calculations for Economy ("Econ")
    for w in [3, 5]:
        features[f'Mean_Econ_{w}'] = df_2023['Econ'].tail(w).mean()
        features[f'Std_Econ_{w}'] = df_2023['Econ'].tail(w).std()

    for w in [3, 5]:
        features[f'Sum_Balls_{w}'] = df_2023['Balls'].tail(w).sum()

    for w in [3, 5]:
        features[f'Sum_Wkts_{w}'] = df_2023['Wkts'].tail(w).sum()

    # Weighted economy: runs conceded per over across the window
    for w in [3, 5]:
        runs_sum = df_2023['Runs'].tail(w).sum()
        balls_sum = df_2023['Balls'].tail(w).sum()
        if balls_sum == 0:
            features[f'Weighted_Econ_{w}'] =0
        else:
            features[f'Weighted_Econ_{w}'] = (runs_sum / ((balls_sum / 6)))

    # Wicket Rate (wickets per over)
    for w in [3, 5]:
        wkts_sum = df_2023['Wkts'].tail(w).sum()
        balls_sum = df_2023['Balls'].tail(w).sum()
        if balls_sum==0:
            features[f'Wkt_Rate_{w}'] =0
        else:
            features[f'Wkt_Rate_{w}'] = (wkts_sum / ((balls_sum / 6)))

    # Fantasy efficiency: fantasy points per ball bowled
    for w in [3, 5]:
        fan_sum = df_2023['FantasyPoints'].tail(w).sum()
        balls_sum = df_2023['Balls'].tail(w).sum()
        if balls_sum == 0:
            features[f'Fan_Efficiency_{w}'] =0
        else:
            features[f'Fan_Efficiency_{w}'] = (fan_sum / (balls_sum))

    for w in [3, 5]:
        wkts_sum = df_2023['Wkts'].tail(w).sum()
        balls_sum = df_2023['Balls'].tail(w).sum()
        # If no wickets taken, use a high strike rate
        if wkts_sum==0:
            features[f'Strike_Rate_{w}'] = 999
        else:
            features[f'Strike_Rate_{w}'] = (balls_sum / (wkts_sum))

    df = df.sort_values('Start Date')
    df = df[df['Start Date'] < cut_date]
    df_2023 = df[df['Start Date'].dt.year >= 2023]
    df_2023.loc[:, 'Balls'] = df_2023['Overs'].apply(convert_overs_to_balls)
    df_2023 = df_2023[['Start Date','Balls','Ground', 'Overs', 'Mdns', 'Inns','Wkts', 'Runs', 'Econ', 'FantasyPoints']].copy()
    features = bowling_venue_features(features, df_2023, ground)
    return pd.DataFrame([features])


def allrounder_batting_prediction_features(file_path, cut_date):
    """Batting form over the last 10 innings, with ``bat_`` prefixed names."""
    df = pd.read_csv(file_path)
    df.columns = df.columns.str.strip()

    required_columns = {'Start Date', 'Runs', 'FantasyPoints'}
    if not required_columns.issubset(df.columns):
        return None

    df['Start Date'] = pd.to_datetime(df['Start Date'], errors='coerce')
    df = df[df['Start Date'] < cut_date]
    df_2023 = df[df['Start Date'].dt.year >= 2023][['Start Date', 'Ground', 'Runs', 'BF', 'FantasyPoints', '4s', '6s']].copy()
    df_2023 = df_2023.dropna()
    df_2023["Runs"] = df_2023['Runs'].fillna(0)
    df_2023["BF"] = df_2023['BF'].fillna(0)
    df_2023["4s"] = df_2023['4s'].fillna(0)
    df_2023["6s"] = df_2023['6s'].fillna(0)

    df_2023 = df_2023.sort_values('Start Date').tail(10)

    runs = df_2023['Runs']
    bf = df_2023['BF']
    fantasy = df_2023['FantasyPoints']
    fours = df_2023['4s']
    sixes = df_2023['6s']
    boundaries = fours + sixes

    features = {}

    # Rolling stats
    for window in [2, 3, 4, 5, 6]:
        features[f'bat_Mean_Run_{window}'] = runs.tail(window).mean() if len(runs) >= window else np.nan
        features[f'bat_Std_Run_{window}'] = runs.tail(window).std() if len(runs) >= window else np.nan
        features[f'bat_Mean_Fan_{window}'] = fantasy.tail(window).mean() if len(fantasy) >= window else np.nan
        features[f'bat_Std_Fan_{window}'] = fantasy.tail(window).std() if len(fantasy) >= window else np.nan

    # 4s and 6s
    for window in [2, 4, 6]:
        features[f'bat_Mean_4s_{window}'] = fours.tail(window).mean() if len(fours) >= window else np.nan
        features[f'bat_Sum_4s_{window}'] = fours.tail(window).sum() if len(fours) >= window else np.nan
        features[f'bat_Mean_6s_{window}'] = sixes.tail(window).mean() if len(sixes) >= window else np.nan
        features[f'bat_Sum_6s_{window}'] = sixes.tail(window).sum() if len(sixes) >= window else np.nan
        features[f'bat_Mean_Boundaries_{window}'] = boundaries.tail(window).mean() if len(boundaries) >= window else np.nan
        features[f'bat_Sum_Boundaries_{window}'] = boundaries.tail(window).sum() if len(boundaries) >= window else np.nan
        features[f'bat_Boundary_Ratio_{window}'] = (
            (boundaries.tail(window).sum() / bf.tail(window).sum()) * 100
            if bf.tail(window).sum() > 0 else np.nan
        )

    for threshold in range(10, 101, 10):
        col_name = f'bat_Perc_Run_gt_{threshold}_10'
        features[col_name] = (
            (runs > threshold).tail(5).sum() / 10.0 * 100
            if len(runs) >= 10 else np.nan
        )

    for w in [3, 5]:
        features[f'bat_Median_Run_{w}'] = runs.tail(w).median() if len(runs) >= w else np.nan

    # Strike rate
    sr = (runs / bf) * 100
    sr = sr.where(bf > 10, 0)
    for w in [3, 5]:
        features[f'bat_Mean_SR_{w}'] = sr.tail(w).mean() if len(sr) >= w else np.nan

    # Masked SR Ratio
    runs_masked = runs.where(bf > 10, 0)
    bf_masked = bf.where(bf > 10, 0)
    for w in [3, 5]:
        runs_sum = runs_masked.tail(w).sum()
        bf_sum = bf_masked.tail(w).sum()
        features[f'bat_SR_ratio_{w}'] = (runs_sum / bf_sum * 100) if bf_sum > 0 else np.nan

    return pd.DataFrame([features])


def allrounder_bowling_prediction_features(file_path, cut_date):
    """Bowling form over the last 10 innings, with ``bowl_`` prefixed names."""
    df = pd.read_csv(file_path)
    df.columns = df.columns.str.strip()

    required_columns = {'Start Date', 'Overs', 'Mdns', 'Inns', 'Runs', 'Wkts', 'Econ', 'FantasyPoints'}
    if not required_columns.issubset(df.columns):
        return None

    df['Start Date'] = pd.to_datetime(df['Start Date'], errors='coerce')
    df = df[df['Start Date'] < cut_date]
    df_2023 = df[df['Start Date'].dt.year >= 2023][['Start Date', 'Ground', 'Overs', 'Mdns', 'Inns', 'Runs', 'Wkts', 'Econ', 'FantasyPoints']].copy()

    df_2023 = df_2023.dropna()
    df_2023['Balls'] = df_2023['Overs'].apply(convert_overs_to_balls)
    df_2023['Runs'] = df_2023['Runs'].fillna(0)
    df_2023['Wkts'] = df_2023['Wkts'].fillna(0)
    df_2023 = df_2023.sort_values('Start Date').tail(10)

    runs = df_2023['Runs']
    wkts = df_2023['Wkts']
    econ = df_2023['Econ']
    fantasy = df_2023['FantasyPoints']
    balls = df_2023['Balls']

    features = {}

    # Rolling stats
    for window in [2, 3, 4, 5, 6]:
        features[f'bowl_Mean_Run_{window}'] = runs.tail(window).mean() if len(runs) >= window else np.nan
        features[f'bowl_Std_Run_{window}'] = runs.tail(window).std() if len(runs) >= window else np.nan
        features[f'bowl_Mean_Fan_{window}'] = fantasy.tail(window).mean() if len(fantasy) >= window else np.nan
        features[f'bowl_Std_Fan_{window}'] = fantasy.tail(window).std() if len(fantasy) >= window else np.nan
        features[f'bowl_Mean_Econ_{window}'] = econ.tail(window).mean() if len(econ) >= window else np.nan
        features[f'bowl_Std_Econ_{window}'] = econ.tail(window).std() if len(econ) >= window else np.nan

    for window in [2, 4, 6]:
        features[f'bowl_Mean_Wkts_{window}'] = wkts.tail(window).mean() if len(wkts) >= window else np.nan
        features[f'bowl_Std_Wkts_{window}'] = wkts.tail(window).std() if len(wkts) >= window else np.nan

    for threshold in range(10, 101, 10):
        features[f'bowl_Perc_Run_gt_{threshold}_10'] = (
            (runs > threshold).tail(5).sum() / 10.0 * 100
            if len(runs) >= 10 else np.nan
        )

    for threshold in [1, 2, 3, 4, 5]:
        features[f'bowl_Perc_Wkts_gt_{threshold}_10'] = (
            (wkts >= threshold).tail(5).sum() / 10.0 * 100
            if len(wkts) >= 10 else np.nan
        )

    for w in [3, 5]:
        features[f'bowl_Median_Run_{w}'] = runs.tail(w).median() if len(runs) >= w else np.nan
        features[f'bowl_Median_Wkts_{w}'] = wkts.tail(w).median() if len(wkts) >= w else np.nan
        features[f'bowl_Sum_Balls_{w}'] = balls.tail(w).sum() if len(balls) >= w else np.nan
        features[f'bowl_Sum_Wkts_{w}'] = wkts.tail(w).sum() if len(wkts) >= w else np.nan

        runs_sum = runs.tail(w).sum()
        balls_sum = balls.tail(w).sum()
        wkts_sum = wkts.tail(w).sum()
        fan_sum = fantasy.tail(w).sum()

        features[f'bowl_Weighted_Econ_{w}'] = (runs_sum / (balls_sum / 6)) if balls_sum > 0 else np.nan
        features[f'bowl_Wkt_Rate_{w}'] = (wkts_sum / (balls_sum / 6)) if balls_sum > 0 else np.nan
        features[f'bowl_Fan_Efficiency_{w}'] = (fan_sum / balls_sum) if balls_sum > 0 else np.nan
        features[f'bowl_Strike_Rate_{w}'] = (balls_sum / wkts_sum) if wkts_sum > 0 else 999

    return pd.DataFrame([features])
