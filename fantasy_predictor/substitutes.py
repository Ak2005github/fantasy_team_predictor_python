"""Stage 1h: record zero-point appearances for substitutes and benched players.

For every earlier match, a substitute or non-playing squad member gets a row
for that match date (copied from a team-mate who played, with the stats
zeroed), so their rolling form reflects the matches they sat out.
"""
import os

import pandas as pd

from .config import MATCH_DATES_CSV, PLAYER_ID_CSV, PLAYERS_DIR, SQUAD_WORKBOOK

STAT_COLUMNS = {
    "bat": ["Runs", "Mins", "BF", "4s", "6s", "SR", "Pos", "FantasyPoints"],
    "bowl": ["Overs", "BPO", "Mdns", "Runs", "Wkts", "Econ", "Pos", "FantasyPoints"],
    "field": ["Dis", "Ct", "St", "Ct Wk", "Ct Fi", "Catch Points", "Catch Bonus", "Stumping Points", "FantasyPoints"],
}


def copy_common_columns_by_date(source_path, target_path, date):
    """Copy the source file's rows for ``date`` into the target file. Returns True if rows were added."""
    input_date = pd.to_datetime(date).normalize()

    df_source = pd.read_csv(source_path, parse_dates=['Start Date'])
    df_target = pd.read_csv(target_path, parse_dates=['Start Date'])

    if 'Start Date' in df_source.columns and df_source['Start Date'].notna().any():
        df_source['Start Date'] = df_source['Start Date'].dt.normalize()

    if 'Start Date' in df_target.columns and df_target['Start Date'].notna().any():
        df_target['Start Date'] = df_target['Start Date'].dt.normalize()

    if input_date in df_target['Start Date'].values:
        return False  # nothing copied

    common_cols = df_source.columns.intersection(df_target.columns)
    rows_to_copy = df_source[df_source['Start Date'] == input_date][common_cols]

    if rows_to_copy.empty:
        return False  # nothing copied

    # Drop rows that are completely NaN
    rows_to_copy = rows_to_copy.dropna(how='all')

    # Only proceed if rows_to_copy has some usable data
    if not rows_to_copy.empty:
        if df_target.empty:
            df_target = rows_to_copy.reset_index(drop=True)
        else:
            df_target = pd.concat([df_target, rows_to_copy], ignore_index=True)

    df_target = df_target.sort_values(by='Start Date').reset_index(drop=True)
    df_target.to_csv(target_path, index=False)

    return True  # rows were copied


def zero_specific_columns_by_date(target_path, date, data_type):
    """Set the performance columns of the row(s) on ``date`` to zero."""
    input_date = pd.to_datetime(date).normalize()

    df = pd.read_csv(target_path, parse_dates=['Start Date'])
    df['Start Date'] = df['Start Date'].dt.normalize()

    if data_type not in STAT_COLUMNS:
        return

    cols_to_zero = [col for col in STAT_COLUMNS[data_type] if col in df.columns]

    # Apply zeroing for the specific date row
    mask = df['Start Date'] == input_date
    if not mask.any():
        return

    df.loc[mask, cols_to_zero] = 0
    df.to_csv(target_path, index=False)


def _find_partner(team_playing, role, name_to_id, date_of_match, players_dir):
    """First player of ``role`` in the playing XI whose file has a row on the match date."""
    for _, row in team_playing[team_playing['Player Type'] == role].iterrows():
        pid = name_to_id.get(row['Player Name'])
        if pid is None:
            continue

        path = os.path.join(players_dir, str(pid), f"{pid}_{role.lower()}.csv")
        if not os.path.exists(path):
            continue
        try:
            df = pd.read_csv(path, parse_dates=['Start Date'])
        except Exception:
            continue
        # check for at least one matching date
        if (df['Start Date'].dt.date == date_of_match).any():
            return pid
    return None


def backfill_substitute_matches(match_number, id_csv=PLAYER_ID_CSV, dates_csv=MATCH_DATES_CSV,
                                workbook_path=SQUAD_WORKBOOK, players_dir=PLAYERS_DIR):
    """Add zeroed rows for substitutes and benched players in matches 1 .. match_number-1."""
    id_of_players_df = pd.read_csv(id_csv)
    name_to_id = id_of_players_df.set_index("Player Name")["PlayerID"].to_dict()

    matches_dates = pd.read_csv(dates_csv)
    matches_dates["Date"] = pd.to_datetime(matches_dates["Date"],format="%d-%m-%Y").dt.date
    match_date_dict = matches_dates.set_index("Match Number")["Date"].to_dict()

    excel_file1 = pd.ExcelFile(workbook_path)  # loads just the metadata
    for i in range(1, match_number):
        sheet = f"Match_{i}"

        # skip if the sheet isn't in this workbook
        if sheet not in excel_file1.sheet_names:
            continue

        squad = pd.read_excel(workbook_path, sheet_name=f"Match_{i}")
        playing = squad[squad['IsPlaying'] == 'PLAYING']
        date_of_match = match_date_dict.get(i)  # a datetime.date

        # per-team partner whose row on that date can be copied
        bat_partner_map  = {}
        bowl_partner_map = {}
        for team in playing['Team'].unique():
            team_playing = playing[playing['Team'] == team]
            bat_partner_map[team] = _find_partner(team_playing, 'BAT', name_to_id, date_of_match, players_dir)
            bowl_partner_map[team] = _find_partner(team_playing, 'BOWL', name_to_id, date_of_match, players_dir)

        subs = squad[squad['IsPlaying'].isin(['X_FACTOR_SUBSTITUTE', 'NOT_PLAYING'])]
        for _, sub in subs.iterrows():
            sub_name = sub['Player Name']
            sub_type = sub['Player Type']
            sub_team = sub['Team']
            sub_id   = name_to_id.get(sub_name)
            if sub_id is None:
                continue

            bat_partner  = bat_partner_map.get(sub_team)
            bowl_partner = bowl_partner_map.get(sub_team)

            # decide which files to "fill"
            if sub_type in ('BAT', 'WK'):
                file_types, partner_ids = ['bat','field'], [bat_partner, bat_partner]
            elif sub_type == 'BOWL':
                file_types, partner_ids = ['bowl','field'], [bowl_partner, bowl_partner]
            else:
                file_types  = ['bat','bowl','field']
                partner_ids = [bat_partner, bowl_partner, bat_partner]

            for ftype, partner_id in zip(file_types, partner_ids):
                if partner_id is None:
                    # no valid partner found
                    continue
                csv_path = os.path.join(players_dir, str(sub_id), f"{sub_id}_{ftype}.csv")
                if not os.path.exists(csv_path):
                    continue
                part_source_path = os.path.join(players_dir, str(partner_id), f"{partner_id}_{ftype}.csv")
                added = copy_common_columns_by_date(part_source_path, csv_path, date_of_match)
                if added:
                    zero_specific_columns_by_date(csv_path, date_of_match, ftype)
