"""File locations, external endpoints and secrets used across the pipeline.

All paths are relative to the working directory the pipeline is started
from, exactly as in the original notebook script.
"""
import os

SQUAD_WORKBOOK = "data/SquadPlayerNames_IndianT20League.xlsx"
PLAYER_ID_CSV = "Final_id_data_all.csv"
PLAYERS_DIR = "Data_players"
GROUND_TABLE_CSV = "sort_gr_coun_full_name.csv"
MATCHES_CSV = "ipl_2025_matches.csv"
MATCHES_CORRECTED_CSV = "ipl_2025_matches_corrected.csv"
MATCH_DATES_CSV = "ipl_match_dates.csv"
POINTS_TABLE_CSV = "ipl_2025_points_table.csv"
MERGED_BAT_CSV = "merged_bat_bhav.csv"
MERGED_BOWL_CSV = "merged_bowl_bhav.csv"
MERGED_COMBINED_CSV = "merged_combined.csv"
OUTPUT_CSV = "data/Ignitors_output.csv"
RESUME_FLAG = "data/resume.flag"

CRICBUZZ_FIXTURES_URL = "https://www.cricbuzz.com/cricket-series/9237/indian-premier-league-2025/matches"
WIKIPEDIA_SEASON_URL = "https://en.wikipedia.org/wiki/2025_Indian_Premier_League"

# CricAPI identifier of the IPL 2025 series. This is not a secret.
CRICAPI_SERIES_ID = "d5a498c8-7596-4b93-8ab0-e0efc3345312"
CRICAPI_KEY_ENV = "CRICAPI_KEY"


def cricapi_key():
    """Return the CricAPI key from the environment, failing early with a clear message."""
    key = os.environ.get(CRICAPI_KEY_ENV, "").strip()
    if not key:
        raise RuntimeError(
            f"Set the {CRICAPI_KEY_ENV} environment variable to your CricAPI key "
            "before running the pipeline."
        )
    return key
