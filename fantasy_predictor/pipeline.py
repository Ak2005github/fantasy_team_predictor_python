"""End-to-end run for one match, in the same order as the original notebook.

Step 1 (before the toss) scrapes and scores every player's history and
builds the training tables. The run then pauses until ``data/resume.flag``
exists, so it can be resumed once lineups and the toss are announced.
Step 2 trains the models, predicts each player's points and picks the XI.
"""
import os
import random
import time

import numpy as np
import pandas as pd

from . import cleaning, cricapi, features_training, grounds, models, optimizer, schedule, scoring, squad, substitutes
from .config import (CRICAPI_SERIES_ID, OUTPUT_CSV, PLAYER_ID_CSV, RESUME_FLAG, SQUAD_WORKBOOK, cricapi_key)
from .cricket import innings_map, resolve_toss_winner
from .player_ids import build_player_id_file
from .scraper import scrape_players


def seed_everything(seed=42):
    os.environ["PYTHONHASHSEED"] = "0"
    random.seed(seed)
    np.random.seed(seed)


def wait_for_resume(flag_path=RESUME_FLAG):
    """
    Pause execution until the flag file exists.
    Removes the flag afterward to keep the workspace clean.
    """
    print(f"📍 Paused. Waiting for '{flag_path}' to exist...")
    while not os.path.exists(flag_path):
        time.sleep(60)
    print("✅ Resume signal received. Continuing...")
    os.remove(flag_path)


def run_step1(match_number, apikey):
    """Scrape, score and build training tables. Returns (match list, step-1 venue)."""
    # Squad workbook housekeeping
    squad.normalize_sheet_names(SQUAD_WORKBOOK)
    squad.add_new_players_to_master(SQUAD_WORKBOOK, match_number)
    squad.unify_player_types(SQUAD_WORKBOOK, match_number)

    # Player IDs and innings history
    players = build_player_id_file(SQUAD_WORKBOOK, PLAYER_ID_CSV)
    scrape_players(players)
    scoring.score_all_player_files()

    grounds.build_ground_table()
    cleaning.align_columns_and_dates()
    cleaning.drop_unnamed_columns()

    # Season fixtures, then zero-point rows for benched players
    schedule.scrape_fixtures()
    schedule.build_fixture_tables()
    substitutes.backfill_substitute_matches(match_number)

    ipl_matches_list = cricapi.get_series_info(apikey, CRICAPI_SERIES_ID)['data']['matchList']
    match_info, cut_date = cricapi.match_info_from_schedule(apikey, ipl_matches_list, match_number)

    features_training.build_batting_training_table(cut_date)
    features_training.build_bowling_training_table(cut_date)
    features_training.build_allrounder_training_table(cut_date)

    return ipl_matches_list, match_info['data']['venue']


def run_step2(match_number, apikey, ipl_matches_list, venue_step1):
    """Train, predict and select the team. Returns the saved team as a DataFrame."""
    match_info, cut_date = cricapi.match_info_by_number(apikey, ipl_matches_list, match_number)

    squad_df = pd.read_excel(SQUAD_WORKBOOK, sheet_name=f"Match_{match_number}")
    id_table = pd.read_csv(PLAYER_ID_CSV)
    ground_table = grounds.load_ground_table()

    schedule.scrape_points_table()
    team_codes = schedule.load_team_codes()
    toss_code = team_codes[match_info["data"]["tossWinner"]]
    toss_choice = match_info['data']['tossChoice']
    teams = list(squad_df['Team'].unique())

    id_of_match = models.match_players(squad_df, id_table)

    # The batting and bowling models use the venue known in step 1; the all-rounder model uses step 2's
    ground_step1 = grounds.find_ground_info(ground_table, venue_step1)[0]
    bat_preds = models.predict_batting_points(
        id_of_match, innings_map(teams, toss_code, toss_choice), cut_date, ground_step1)
    bowl_preds = models.predict_bowling_points(
        id_of_match, innings_map(teams, toss_code, toss_choice, bowling=True), cut_date, ground_step1)

    ground_step2 = grounds.find_ground_info(ground_table, match_info['data']['venue'])[0]
    all_preds = models.predict_allrounder_points(
        id_of_match, innings_map(teams, toss_code, toss_choice), cut_date, ground_step2)

    df_match_players = squad_df
    toss_winner = resolve_toss_winner(list(df_match_players['Team'].unique()),
                                      team_codes.get(match_info['data']['tossWinner']))
    players = optimizer.prepare_players(df_match_players, bat_preds, bowl_preds, all_preds,
                                        toss_winner, toss_choice)
    return optimizer.solve(players, df_match_players, OUTPUT_CSV)


def run(match_number):
    seed_everything()
    apikey = cricapi_key()  # fail before the long scraping step if the key is missing

    ipl_matches_list, venue_step1 = run_step1(match_number, apikey)
    print("STEP 1 COMPLETE")

    wait_for_resume()
    print("STEP 2 COMPLETE")

    team = run_step2(match_number, apikey, ipl_matches_list, venue_step1)
    print(f"Team saved to {OUTPUT_CSV}")
    return team
