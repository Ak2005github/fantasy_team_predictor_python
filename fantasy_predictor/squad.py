"""Stage 1a: keep the squad workbook consistent before scraping.

These steps edit the workbook in place, as the original script did.
"""
import re

import openpyxl
import pandas as pd


def normalize_sheet_names(workbook_path):
    """Drop helper sheets and shift match sheets numbered 60+ down by two."""
    workbook = openpyxl.load_workbook(workbook_path)

    # Step 1: Delete 'matchnum_mapping' and 'cancelled' sheets if they exist
    sheets_to_delete = ['MatchNum_Mapping', 'canceled']
    for sheet in sheets_to_delete:
        if sheet in workbook.sheetnames:
            del workbook[sheet]

    # Step 2: Rename sheets like "Match_60", "Match_61", etc. if the number >= 60
    pattern = re.compile(r"Match_(\d+)")
    new_sheetnames = {}

    for sheet in workbook.sheetnames:
        match = pattern.fullmatch(sheet)
        if match:
            sheet_num = int(match.group(1))
            if sheet_num >= 60:
                new_sheetnames[sheet] = f"Match_{sheet_num - 2}"

    # Perform the renaming
    for old_name, new_name in new_sheetnames.items():
        worksheet = workbook[old_name]
        worksheet.title = new_name

    workbook.save(workbook_path)


def add_new_players_to_master(workbook_path, match_number):
    """Append players who appear in match sheets but not in the master squad sheet."""
    # Read all sheets into a dictionary of DataFrames
    all_sheets = pd.read_excel(workbook_path, sheet_name=None)
    sheet_names = list(all_sheets.keys())

    # First sheet = base reference
    first_sheet_name = sheet_names[0]
    df_first = all_sheets[first_sheet_name]
    players_first = set(df_first["Player Name"].dropna().astype(str).str.strip())

    # Loop through other sheets starting from the 3rd one
    for sheet in sheet_names[2:(match_number + 1)]:
        df_other = all_sheets[sheet]

        # Clean player names
        df_other["Player Name"] = df_other["Player Name"].astype(str).str.strip()
        players_other = set(df_other["Player Name"].dropna())

        # Find players not in the first sheet
        new_players = players_other - players_first

        if new_players:
            # Get only relevant rows and columns
            new_rows = df_other[df_other["Player Name"].isin(new_players)][
                ["Player Name", "Player Type", "Credits", "Team"]
            ].copy()

            # Append to first sheet's DataFrame
            df_first = pd.concat([df_first, new_rows], ignore_index=True)

            # Update the players_first set
            players_first.update(new_players)

    all_sheets[first_sheet_name] = df_first

    # Save back to the same Excel file with all sheets
    with pd.ExcelWriter(workbook_path, engine='openpyxl', mode='w') as writer:
        for sheet_name, df in all_sheets.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)


def unify_player_types(workbook_path, match_number):
    """Mark a player as an all-rounder when match sheets list them as both batter and bowler."""
    all_sheets = pd.read_excel(workbook_path, sheet_name=None)
    sheet_names = list(all_sheets.keys())

    full_sheet1_df = all_sheets[sheet_names[0]].copy()

    # Build player type map
    player_types = dict(zip(full_sheet1_df["Player Name"].str.lower(), full_sheet1_df["Player Type"]))
    changes = []

    # Loop through match sheets (skip Match 0)
    for sheet_name in sheet_names[2:(match_number + 1)]:
        team_df = all_sheets[sheet_name]

        for _, row in team_df.iterrows():
            name = row["Player Name"]
            match_type = row["Player Type"]
            name_lower = name.lower()

            if name_lower not in player_types:
                continue

            sheet1_type = player_types[name_lower]

            if sheet1_type == "ALL":
                continue

            if match_type == "ALL":
                changes.append((name, sheet1_type, "ALL", sheet_name))
                player_types[name_lower] = "ALL"
            elif match_type != sheet1_type:
                type_pair = {match_type, sheet1_type}
                if "BOWL" in type_pair and ("BAT" in type_pair or "WK" in type_pair):
                    changes.append((name, sheet1_type, "ALL", sheet_name))
                    player_types[name_lower] = "ALL"

    # Apply updated types
    for i, row in full_sheet1_df.iterrows():
        name_lower = row["Player Name"].lower()
        if name_lower in player_types:
            full_sheet1_df.at[i, "Player Type"] = player_types[name_lower]

    all_sheets[sheet_names[0]] = full_sheet1_df

    with pd.ExcelWriter(workbook_path, engine='openpyxl', mode='w') as writer:
        for sheet, df in all_sheets.items():
            df.to_excel(writer, sheet_name=sheet, index=False)
    return changes
