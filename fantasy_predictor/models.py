"""Stage 2b: train the three CatBoost models and predict each squad player's fantasy points.

* batting model: trained on every batting innings, predicts batters and keepers
* bowling model: trained on every bowling innings, predicts bowlers
* all-rounder model: trained on matches where a player both batted and bowled
"""
import os

import pandas as pd
from catboost import CatBoostRegressor

from .config import MERGED_BAT_CSV, MERGED_BOWL_CSV, MERGED_COMBINED_CSV, PLAYERS_DIR
from .features_prediction import (allrounder_batting_prediction_features,
                                  allrounder_bowling_prediction_features, batting_prediction_features,
                                  bowling_prediction_features)

CATBOOST_PARAMS = dict(
    iterations=500,
    learning_rate=0.05,
    depth=5,
    random_seed=42,  # fixed seed for reproducible predictions
    verbose=False,
)

BATTING_TRAIN_DROP = ["Runs", "Start Date", "PlayerID", "BF", "4s", "6s"]
BOWLING_TRAIN_DROP = ["Pos", "BPO", "Runs", "Opposition", "PlayerID", "Ground Link", "match_id", "Overs",
                      "Team Link", "Mdns", "Econ", "Balls", "Start Date", "Wkts"]
ALLROUNDER_TRAIN_DROP = [
    'Total_fantasy', 'bat_FantasyPoints', 'bowl_FantasyPoints', 'Start Date', 'PlayerID',
    'bat_Runs', 'bat_BF', 'bat_4s', 'bat_6s', 'bowl_BPO',
    'bowl_Overs', 'bowl_Mdns', 'bowl_BowlInns', 'bowl_Runs', 'bowl_Wkts',
    'bowl_Econ', 'bowl_Balls'
]
# Columns present on only one side (training table or prediction rows) of the all-rounder model
ALLROUNDER_TRAIN_ONLY = ['bowl_Team Link', 'bowl_Ground Link', 'bat_Std_4s_4', 'bat_Std_6s_2', 'bat_Std_4s_6',
                         'bat_Std_6s_6', 'bat_Std_4s_2', 'bowl_Opposition', 'bowl_match_id',
                         'bat_Std_Boundaries_6', 'bowl_Pos', 'bat_Std_Boundaries_4', 'bat_Std_SR_5',
                         'bat_Std_Boundaries_2', 'bat_Std_SR_3', 'bat_Std_6s_4']
ALLROUNDER_PREDICT_ONLY = ['bowl_Mean_Econ_2', 'bowl_Mean_Econ_6', 'bowl_Mean_Econ_4', 'bowl_Std_Econ_2',
                           'bowl_Std_Econ_4', 'bowl_Std_Econ_6']


def match_players(squad_df, id_table):
    """The match squad with each player's ID (players without an ID are dropped)."""
    id_of_match = pd.DataFrame()
    id_of_match["Player Name"] = squad_df["Player Name"]
    id_of_match["Team"] = squad_df["Team"]
    id_of_match["PlayerID"] = id_of_match["Player Name"].map(
        id_table.set_index("Player Name")["PlayerID"]
    )
    id_of_match.dropna(inplace=True)
    id_of_match["PlayerID"] = id_of_match["PlayerID"].astype(int)
    return id_of_match


def _player_rows(id_of_match, build):
    """Stack ``build(pid)`` for every squad player into one frame indexed by PlayerID."""
    all_dfs = []
    for pid in id_of_match['PlayerID']:
        df_player = build(pid)
        if df_player is None or df_player.empty:
            continue
        df_player['PlayerID'] = pid
        all_dfs.append(df_player)

    if all_dfs:
        final_df = pd.concat(all_dfs, ignore_index=True)
    else:
        final_df = pd.DataFrame()
    final_df.set_index("PlayerID", inplace=True)
    return final_df


def _attach_innings(final_df, id_of_match, inns_map):
    """Add each player's innings number (1 or 2) for this match."""
    team_map = id_of_match.set_index('PlayerID')['Team']
    final_df['Team'] = final_df.index.to_series().map(team_map)
    final_df['Inns'] = final_df['Team'].map(inns_map)
    final_df.drop(columns='Team', inplace=True)


def _train(X_train, y_train):
    model = CatBoostRegressor(**CATBOOST_PARAMS)
    model.fit(X_train, y_train)
    return model


def _with_match_ground(frame, ground_cols, index, ground):
    """One-hot encode the match ground using the training table's ground columns."""
    zeros_df = pd.DataFrame(0, index=index, columns=ground_cols)
    frame = pd.concat([frame, zeros_df], axis=1)
    frame[f"Ground_{ground}"] = 1
    return frame


def _predictions(preds, index, id_of_match):
    res = pd.DataFrame(preds, index=index, columns=['PredictedFantasyPoints'])
    name_map = id_of_match.set_index('PlayerID')['Player Name']
    res['Player Name'] = res.index.map(name_map)
    return res[['Player Name', 'PredictedFantasyPoints']]


def _player_file(players_dir, pid, kind):
    return os.path.join(players_dir, str(pid), f"{pid}_{kind}.csv")


def predict_batting_points(id_of_match, inns_map, cut_date, ground,
                           merged_csv=MERGED_BAT_CSV, players_dir=PLAYERS_DIR):
    def build(pid):
        csv_path = _player_file(players_dir, pid, "bat")
        if not os.path.isfile(csv_path):
            return None
        return batting_prediction_features(csv_path, cut_date, ground)

    final_df = _player_rows(id_of_match, build)
    _attach_innings(final_df, id_of_match, inns_map)

    df = pd.read_csv(merged_csv)
    df.drop(columns=BATTING_TRAIN_DROP, inplace=True)
    df1 = pd.get_dummies(df, columns=['Ground'], dtype=int)
    X = df1.loc[:, ~df1.columns.isin(["FantasyPoints"])]
    y = df1['FantasyPoints']
    model = _train(X, y)

    ground_cols = [c for c in df1.columns if c.startswith("Ground_")]
    final_df = _with_match_ground(final_df, ground_cols, final_df.index, ground)
    preds = model.predict(final_df)
    return _predictions(preds, final_df.index, id_of_match)


def predict_bowling_points(id_of_match, inns_map, cut_date, ground,
                           merged_csv=MERGED_BOWL_CSV, players_dir=PLAYERS_DIR):
    def build(pid):
        csv_path = _player_file(players_dir, pid, "bowl")
        if not os.path.isfile(csv_path):
            return None
        return bowling_prediction_features(csv_path, cut_date, ground)

    final_df = _player_rows(id_of_match, build)
    _attach_innings(final_df, id_of_match, inns_map)

    df = pd.read_csv(merged_csv)
    df.drop(columns=BOWLING_TRAIN_DROP, inplace=True)
    df.rename(columns={"BowlInns": "Inns"}, inplace=True)
    df1 = pd.get_dummies(df, columns=['Ground'], dtype=int, drop_first=True)
    X = df1.loc[:, ~df1.columns.isin(["FantasyPoints"])]
    y = df1['FantasyPoints']
    model = _train(X, y)

    ground_cols = [c for c in df1.columns if c.startswith("Ground_")]
    final_df = _with_match_ground(final_df, ground_cols, final_df.index, ground)
    preds = model.predict(final_df)
    return _predictions(preds, final_df.index, id_of_match)


def predict_allrounder_points(id_of_match, inns_map, cut_date, ground,
                              merged_csv=MERGED_COMBINED_CSV, players_dir=PLAYERS_DIR):
    def build(pid):
        csv_path_bat = _player_file(players_dir, pid, "bat")
        if not os.path.isfile(csv_path_bat):
            return None
        csv_path_bowl = _player_file(players_dir, pid, "bowl")
        if not os.path.isfile(csv_path_bowl):
            return None

        df_bat = allrounder_batting_prediction_features(csv_path_bat, cut_date)
        if df_bat is None or df_bat.empty:
            return None
        df_bowl = allrounder_bowling_prediction_features(csv_path_bowl, cut_date)
        if df_bowl is None or df_bowl.empty:
            return None
        return pd.concat([df_bat, df_bowl], axis=1, ignore_index=False)

    final_df = _player_rows(id_of_match, build)
    _attach_innings(final_df, id_of_match, inns_map)

    df = pd.read_csv(merged_csv)
    # Drop sparse rows: more than 10 missing values or more than 70 zeros
    df = df[df.isna().sum(axis=1) <= 10]
    df = df[(df == 0).sum(axis=1) <= 70]
    df = df.rename(columns={'bat_BatInns': 'Inns'})
    df.fillna(0, inplace=True)

    ground_encoded = pd.get_dummies(df['Ground'], prefix='Ground')
    ground_encoded = ground_encoded.astype(int)
    df_without_ground = df.drop('Ground', axis=1)

    df_without_ground['Total_fantasy'] = df_without_ground['bat_FantasyPoints'].fillna(0) + df_without_ground['bowl_FantasyPoints'].fillna(0)
    y = df_without_ground['Total_fantasy']

    df_without_ground = df_without_ground.drop(ALLROUNDER_TRAIN_DROP, axis=1)
    df_without_ground_common = df_without_ground.drop(ALLROUNDER_TRAIN_ONLY, axis=1)
    final_df_common = final_df.drop(ALLROUNDER_PREDICT_ONLY, axis=1)
    df_without_ground_common = df_without_ground_common.rename(columns={'bat_Inns': 'Inns'})

    df_with_ground = pd.concat([df_without_ground_common, ground_encoded], axis=1)
    model = _train(df_with_ground, y)

    ground_cols = [c for c in df_with_ground.columns if c.startswith("Ground_")]
    final_df_common = _with_match_ground(final_df_common, ground_cols, final_df.index, ground)
    final_df_common.dropna(inplace=True)

    preds = model.predict(final_df_common)
    return _predictions(preds, final_df_common.index, id_of_match)
