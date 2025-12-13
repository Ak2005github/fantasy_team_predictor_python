import os, random
os.environ["PYTHONHASHSEED"] = "0"   # redundant if set in ENV, but safe
random.seed(42)
import numpy as np
np.random.seed(42)
#!/usr/bin/env python
# coding: utf-8

# In[4]:


#!/usr/bin/env python
# coding: utf-8

# In[1]:


import numpy as np
import pandas as pd
import os
from openpyxl import load_workbook
import requests
from bs4 import BeautifulSoup
import time
import requests
from collections import defaultdict
from datetime import datetime, timezone
import matplotlib as plt
import seaborn as sns
import sklearn
from sklearn.linear_model import LinearRegression
from catboost import CatBoostRegressor
from typing import List

# import warnings
# warnings.filterwarnings("ignore")


# In[ ]:


import sys

# Ensure NumPy is deterministic
os.environ["PYTHONHASHSEED"] = "0"
np.random.seed(42)

if len(sys.argv) > 1:
    match_id_for_prediction = int(sys.argv[1])  # Fetches the first argument
else:
    print("No argument received.")
    sys.exit(1)
# match_id_for_prediction = int("37")

import os
import time
import pandas as pd
import openpyxl
import re

# Load the Excel file
file_path = "data/SquadPlayerNames_IndianT20League.xlsx"
workbook = openpyxl.load_workbook(file_path)

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

# Save the updated workbook to a new file
new_file_path = "data/SquadPlayerNames_IndianT20League.xlsx"
workbook.save(new_file_path)


def wait_for_resume(flag_path="data/resume.flag"):
    """
    Pause execution until the flag file exists.
    Removes the flag afterward to keep the workspace clean.
    """
    print(f"📍 Paused. Waiting for '{flag_path}' to exist...")
    while not os.path.exists(flag_path):
        time.sleep(60)
    print("✅ Resume signal received. Continuing...")
    os.remove(flag_path)  # Optional: auto-cleanup

# In[3]:
from openpyxl import load_workbook
import shutil

# Path to your Excel file
excel_path = "data/SquadPlayerNames_IndianT20League.xlsx"

# Read all sheets into a dictionary of DataFrames
all_sheets = pd.read_excel(excel_path, sheet_name=None)

# Get list of sheet names
sheet_names = list(all_sheets.keys())

# First sheet = base reference
first_sheet_name = sheet_names[0]
df_first = all_sheets[first_sheet_name]
players_first = set(df_first["Player Name"].dropna().astype(str).str.strip())

# Loop through other sheets starting from the 3rd one
for sheet in sheet_names[2:(match_id_for_prediction+1)]:
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

# Update the modified first sheet in the dictionary
all_sheets[first_sheet_name] = df_first

# Save back to the same Excel file with all sheets
with pd.ExcelWriter(excel_path, engine='openpyxl', mode='w') as writer:
    for sheet_name, df in all_sheets.items():
        df.to_excel(writer, sheet_name=sheet_name, index=False)


# In[4]:


# Load Excel file
file_path = "data/SquadPlayerNames_IndianT20League.xlsx"
all_sheets = pd.read_excel(file_path, sheet_name=None)

# Preserve sheet names
sheet_names = list(all_sheets.keys())

# Copy full Sheet 1
full_sheet1_df = all_sheets[sheet_names[0]].copy()

# Build player type map
player_types = dict(zip(full_sheet1_df["Player Name"].str.lower(), full_sheet1_df["Player Type"]))
changes = []

# Loop through match sheets (skip Match 0)
for sheet_name in sheet_names[2:(match_id_for_prediction+1)]:
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

# Replace Sheet 1 and preserve all others
all_sheets[sheet_names[0]] = full_sheet1_df

# Save everything back
with pd.ExcelWriter(file_path, engine='openpyxl', mode='w') as writer:
    for sheet, df in all_sheets.items():
        df.to_excel(writer, sheet_name=sheet, index=False)


# In[5]:


discrepancy_players = {
    "Andre Siddharth": 1440190,
    "Madhav Tiwari": 1460385,
    "Manvanth Kumar L": 1392186,
    "Mohit Sharma": 537119,
    "Lokesh Rahul": 422108,
    "Gurnoor Brar Singh": 1287033,
    "Arshad Khan": 1244751,
    "Ravisrinivasan Sai Kishore": 1048739,
    "Rashid-Khan": 793463,
    "Anukul Sudhakar Roy": 1079839,
    "Digvesh Singh": 1460529,
    "Prince Yadav": 1350768,
    "Mayank Yadav": 1292563,
    "Abdul Samad": 1175485,
    "Shahbaz Ahmed": 1159711,
    "Mohsin Khan": 1132005,
    "Raj Angad Bawa": 1292502,
    "Ashwani Kumar": 1209126,
    "Mujeeb-ur-Rahman": 974109,
    "Rohit Sharma": 34102,
    "Musheer Khan": 1316430,
    "Harnoor Singh Pannu": 1292496,
    "Vyshak Vijaykumar": 777815,
    "Pravin Dubey": 777515,
    "Yash Thakur": 1070196,
    "Abhinandan Singh": 1449085,
    "Philip Salt": 669365,
    "Ashok Sharma": 1299879,
    "Yudhvir Singh Charak": 1206052,
    "Sandeep Sharma": 438362,
    "K Nitish Reddy": 1175496,
    "Simarjeet- Singh": 1159722,
    "Abhishek Sharma": 1070183
}


# In[6]:


# Function to extract player ID from HTML tag
def extract_player_id_from_tag(tag_html):
    if tag_html:
        soup = BeautifulSoup(tag_html, 'html.parser')
        a_tag = soup.find('a', class_='statsLinks', href=True)
        if a_tag:
            href = a_tag['href']
            player_id = href.split('/player/')[-1].split('.html')[0]
            return player_id
    return None

# Function to fetch HTML and extract multiple player IDs
def fetch_player_tags(player_name):
    url = f"https://stats.espncricinfo.com/ci/engine/stats/analysis.html?search={'+'.join(player_name.split())};template=analysis"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/115.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,/;q=0.8"
    }
    timeout = 40

    while True:
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            break  # Exit the loop if successful
        except Exception as e:
            pass

        time.sleep(2)  # Optional delay between retries

    if response.status_code != 200:
        return None

    soup = BeautifulSoup(response.text, 'html.parser')
    player_div = soup.find('div', id='gurusearch_player')
    if not player_div:
        return None

    a_tags = player_div.find_all('a', class_='statsLinks', href=lambda h: h and 'class=6' in h)
    return [extract_player_id_from_tag(str(a_tag)) for a_tag in a_tags]

# Function to add Player IDs to DataFrame and separate multiple IDs
def add_player_ids(df):
    single_ids = []

    for player in df['Player Name']:
        ids = fetch_player_tags(player)
        if ids and len(ids) > 1:
            if player in discrepancy_players:
                single_ids.append(discrepancy_players[player])
        elif ids:
            single_ids.append(ids[0])
        else:
            if player in discrepancy_players:
                single_ids.append(discrepancy_players[player])

    df['PlayerID'] = single_ids

    return df


# In[7]:


df = pd.read_excel("data/SquadPlayerNames_IndianT20League.xlsx",sheet_name='SquadData_AllTeams')


# In[8]:


df = add_player_ids(df)


# In[9]:


df.to_csv("Final_id_data_all.csv")


# In[10]:


df= pd.read_csv("Final_id_data_all.csv",index_col=0)


# In[11]:


def scrape_data(player_id, data_type):

    base_url = f"https://stats.espncricinfo.com/ci/engine/player/{player_id}.html?class=6;template=results;"

    type_mapping = {
        "bat": "type=batting;view=innings",
        "bowl": "type=bowling;view=innings",
        "bowl_wic": "type=bowling;view=dismissal_list",
        "field": "type=fielding;view=innings"
    }
    i_mapping = {
        "bat": 12,
        "bowl": 10,
        "bowl_wic": None,
        "field": 9
    }

    i=i_mapping[data_type]
    if data_type not in type_mapping:
        raise ValueError(f"Invalid data_type: {data_type}. Must be one of {list(type_mapping.keys())}")

    url = base_url + type_mapping[data_type]

    # Get the page content
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/122.0.0.0 Safari/537.36"
    }
    timeout = 40

    while True:
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            break  # Exit the loop if successful
        except requests.exceptions.Timeout:
            pass
        except requests.exceptions.RequestException as e:
            pass

        time.sleep(2)  # Optional delay between retries
    soup = BeautifulSoup(response.text, 'html.parser')

    # Locate all tables with class 'engineTable'
    tables = soup.find_all('table', class_='engineTable')

    # Check if there are enough tables
    if len(tables) < 3:
        return

    # Select the desired table (e.g., 3rd or 4th table)
    table = tables[3]  # Adjust index (2 for 3rd table, 3 for 4th table)

    # Extract table headers
    headers = [th.text.strip() for th in table.find_all('th')]
    headers.append("Ground Link")
    headers.append("Team Link")

    if 'BPO' in headers:
        i+=1

    # Extract table rows
    rows = []
    for tr in table.find_all('tr')[1:]:  # Skip header row
        cells = tr.find_all('td')
        row = [cell.text.strip() for cell in cells]
        # Extract ground hyperlink from the correct column
        if i is not None and len(cells) >= i:
            ground_cell = cells[i-1]  # Ground column
            ground_link_tag = ground_cell.find('a')
            ground_link = "https://stats.espncricinfo.com" + ground_link_tag['href'] if ground_link_tag else ""
        else:
            ground_link = ""

        # Extract team link
        if i is not None and len(cells) >= i-1:
            team_cell = cells[i-2]
            team_link_tag = team_cell.find('a')
            team_link = "https://stats.espncricinfo.com" + team_link_tag['href'] if team_link_tag else ""
        else:
            team_link = ""

        # Append both links to the row
        if row:
            row.append(ground_link)
            row.append(team_link)
            rows.append(row)


    # Ensure headers are not empty
    if not headers and rows:
        headers = [f"Column_{i}" for i in range(len(rows[0]))]

    if not rows:
        return

    df = pd.DataFrame(rows if rows and len(rows[0]) == len(headers) else [], columns=headers)
    save_dir = f"Data_players/{player_id}"
    os.makedirs(save_dir, exist_ok=True)  # Ensure the player_id directory exists

    save_path = f"{save_dir}/{player_id}_{data_type}.csv"
    df.to_csv(save_path, index=False)
    return df


# In[12]:


def process_players(df):
    type_to_queries = {
        "BAT": ["bat", "field"],
        "BOWL": ["bowl", "bowl_wic", "field"],
        "WK": ["bat", "field"],
        "ALL": ["bat", "bowl", "bowl_wic", "field"]
    }
    os.makedirs("Data_players", exist_ok=True)
    for _, row in df.iterrows():
        player_id = row["PlayerID"]
        player_type = row["Player Type"]

        if player_type in type_to_queries:
            for query in type_to_queries[player_type]:
                scrape_data(player_id, query)


# In[13]:


process_players(df)


# In[14]:


def process_fantasy_points_bat(file_path):
    # Read CSV

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

    # Function to determine if the player is out
    def get_out_value(val):
        if val == 'DNB':
            return np.nan     
        elif val.endswith('*'):
            return 0       
        else:
            return 1       

    df['out'] = df['Runs'].apply(get_out_value)
    df['out'] = df['out'].fillna(-1).astype(int)
    df['out'] = df['out'].replace(-1, np.nan)

    df['Runs'] = df['Runs'].astype(str).str.extract(r'(\d+)')[0].astype(float)

    # Convert relevant columns to numeric
    numeric_cols = ['Runs', 'BF', 'SR', '4s', '6s', 'out']
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # Function to calculate fantasy points
    def calculate_fantasy_points(row):
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

    # Apply fantasy points calculation
    df['FantasyPoints'] = df.apply(calculate_fantasy_points, axis=1)

    # Save the modified DataFrame back to the same file
    df.to_csv(file_path, index=False)


# In[15]:


def process_fantasy_points_bowl(file_path, wickets_file_path):
    """
    Reads match data and wicket details, calculates fantasy points for bowling, and saves the updated data.

    Parameters:
    - file_path: str, path to the match-level data file (df)
    - wickets_file_path: str, path to the wickets data file (df1)
    """

    # Read the data
    df = pd.read_csv(file_path)
    df1 = pd.read_csv(wickets_file_path)

    required_columns_df = [
        'Overs', 'Mdns', 'Runs', 'Wkts', 'Econ','Opposition', 'Ground', 'Start Date', 'Ground Link', 'Team Link'
    ]

    # Check if all required columns are in the DataFrame
    missing_columns_df = set(required_columns_df) - set(df.columns)

    required_columns_df1 = [
        'Batter', 'How out', 'Fielder', 'Runs', 'Inns','Opposition', 'Ground', 'Start Date', 'Ground Link', 'Team Link'
    ]

    # Check if all required columns are in the DataFrame
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

    def calculate_bowling_points(row, wickets_df):
        """
        row        : a row from df (bowler's match-level data)
        wickets_df : subset of df1 (all wicket details for this match)
        """
        overs = row['Overs']
        mdns  = row['Mdns']
        runs_conceded = row['Runs']
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

        # (B) Wickets => +25 each (excluding run out)
        points += total_wickets * 30

        # (C) Bonus for LBW/Bowled => +8 each
        points += lbw_bowled_count * 8

        # (D) 3/4/5 Wicket Bonus => highest bracket only
        if total_wickets >= 5:
            points += 12
        elif total_wickets >= 4:
            points += 8
        elif total_wickets >= 3:
            points += 4

        # (E) Maiden Overs => +12 each
        points += mdns * 12

        # (F) Economy Rate Bonus/Penalty (min 2 overs)
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

        mdns_dots = (0 if pd.isna(row['Mdns']) else row['Mdns']) * 6  
        balls1 = (0 if pd.isna(overs) else overs) * 6  
        remaining_balls = balls1 - mdns_dots  
        extras_estimate = (0 if pd.isna(row['Runs']) else row['Runs']) / 5 + (0 if pd.isna(row['Runs']) else row['Runs']) / 3
        dots_from_remaining = remaining_balls - extras_estimate
        total_dots = mdns_dots + dots_from_remaining
        points += max(0, min(24,(round(total_dots))))

        return 0 if pd.isna(points) or points is None else points

    def get_bowling_points(row):
        mid = row['match_id']
        if mid in df1_groups.groups:
            wickets_data = df1_groups.get_group(mid)
        else:
            # No wickets recorded for this match in df1
            wickets_data = pd.DataFrame(columns=df1.columns)
        return calculate_bowling_points(row, wickets_data)

    df['FantasyPoints'] = df.apply(get_bowling_points, axis=1)

    # Save the updated data back to the original file
    df.to_csv(file_path, index=False)


# In[16]:


def process_fantasy_points_field(file_path):
    """
    Reads a fielding stats CSV, calculates fantasy points, and saves it back.

    Fielding Points Calculation:
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


    # Save back
    df.to_csv(file_path, index=False)


# In[17]:


base_dir = "Data_players"
for player_folder in os.listdir(base_dir):  # Loop over player folders
    if os.path.isdir(f"{base_dir}/{player_folder}"):  # Ensure it's a directory
        for file in os.listdir(f"{base_dir}/{player_folder}"):  # Loop over files in the folder
            if file.endswith("_bat.csv"):  # Check if it ends with 'bat.csv'
                process_fantasy_points_bat(f"{base_dir}/{player_folder}/{file}")  # Placeholder for your action
            elif file.endswith("_bowl.csv"):
                process_fantasy_points_bowl(f"{base_dir}/{player_folder}/{file}",f"{base_dir}/{player_folder}/{file[:-4]}_wic.csv")
            elif file.endswith("_field.csv"):
                process_fantasy_points_field(f"{base_dir}/{player_folder}/{file}")


# In[18]:


import pandas as pd
import os

# Set the root folder path
root_folder = "Data_players"

# Prepare a dictionary to store ground value counts
ground_counts = {}

# Traverse all subdirectories and files
for subdir, _, files in os.walk(root_folder):
    for file in files:
        if file.endswith('.csv') and not file.endswith('bowl_wic.csv'):
            file_path = os.path.join(subdir, file)
            try:
                df = pd.read_csv(file_path)

                # Ensure the required columns exist
                if 'Start Date' in df.columns and 'Ground Link' in df.columns:
                    # Convert Start Date to datetime
                    df['Start Date'] = pd.to_datetime(df['Start Date'], errors='coerce')

                    # Filter rows from 2023 onwards
                    filtered_df = df[df['Start Date'] >= pd.Timestamp('2023-01-01')]

                    # Count Ground values
                    ground_counts[file] = filtered_df['Ground Link'].value_counts()

            except Exception as e:
                ground_counts[file] = f"Error: {e}"

# Combine the counts into a DataFrame for viewing
if ground_counts:
    combined_ground_counts = pd.concat(ground_counts, axis=1).fillna(0).astype(int)
    combined_ground_counts["Total"] = combined_ground_counts.sum(axis=1)
else:
    combined_ground_counts = pd.DataFrame()


# In[19]:


# Step 1: Create a mapping from Ground Link to Ground
ground_link_to_name = {}

for subdir, _, files in os.walk(root_folder):
    for file in files:
        if file.endswith('.csv') and not file.endswith('bowl_wic.csv'):
            file_path = os.path.join(subdir, file)
            try:
                df = pd.read_csv(file_path)

                # Ensure both required columns exist
                if 'Ground Link' in df.columns and 'Ground' in df.columns:
                    for _, row in df[['Ground Link', 'Ground']].dropna().iterrows():
                        link = row['Ground Link']
                        name = row['Ground']
                        if link not in ground_link_to_name:
                            ground_link_to_name[link] = name

            except Exception as e:
                pass
# Step 2: Create the 'corr_ground' column using the mapping
combined_ground_counts["corr_ground"] = combined_ground_counts.index.map(ground_link_to_name)


# In[20]:


sorted_ground_counts = combined_ground_counts.sort_values(by='Total', ascending=False)


# In[21]:


# # Extract the number at the end of each URL in the index
sorted_ground_counts["id_gr"] = sorted_ground_counts.index.str.extract(r'(\d+)\.html$')[0].astype(int).values


# In[22]:


headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}

# Function to extract label from each page
def get_ground_label(url_id):
    url = f"https://stats.espncricinfo.com/ci/engine/ground/{url_id}.html?class=6;type=aggregate"

    while True:
        try:
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, "html.parser")
            link_tag = soup.find("a", href="/records")
            if link_tag:
                return link_tag.text.strip()
            else:
                return "Unknown"
        except Exception as e:
            pass


# In[23]:


# Replace index with extracted link text
sorted_ground_counts["Name_gr_ex"] = [get_ground_label(url) for url in sorted_ground_counts['id_gr']]


# In[24]:


# Extract the ground part using string split
sorted_ground_counts["Name_gr_ex"] = sorted_ground_counts["Name_gr_ex"].str.extract(
    r'Statsguru / (.+?) / Twenty20 matches'
)


# In[25]:


sorted_ground_counts.to_csv("sort_gr_coun_full_name.csv")


# In[26]:


root_dir = 'Data_players'
suffixes = ['_bat.csv', '_bowl.csv', '_field.csv']

# ── PASS 1: build max_info ─────────────────────────────────────────────────────
max_info = {s: {'max_cols': 0, 'columns': [], 'file': None} for s in suffixes}

for dirpath, _, filenames in os.walk(root_dir):
    for fname in filenames:
        for suf in suffixes:
            if fname.endswith(suf):
                path = os.path.join(dirpath, fname)
                try:
                    df = pd.read_csv(path)
                except Exception as e:
                    continue
                ncol = df.shape[1]
                if ncol > max_info[suf]['max_cols']:
                    max_info[suf].update({
                        'max_cols': ncol,
                        'columns': df.columns.tolist(),
                        'file': path
                    })
                break


# ── PASS 2: enforce max‑cols + normalize dates ────────────────────────────────
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

            # Normalize Start Date (to YYYY‑MM‑DD strings)
            if 'Start Date' in df.columns:
                df['Start Date'] = (
                    pd.to_datetime(
                        df['Start Date'],
                        dayfirst=True,
                        format = 'mixed'
                        # turns unparseable strings into NaT rather than throwing
                    )
                    
                    # .dt.strftime('%Y-%m-%d')
                )
                df["Start Date"] = df["Start Date"].dt.normalize().dt.strftime("%Y-%m-%d")


            # Overwrite the file
            df.to_csv(path, index=False)
            break


# In[27]:


root_dir = 'Data_players'
suffixes = ['_bat.csv', '_bowl.csv', '_field.csv']

for dirpath, _, filenames in os.walk(root_dir):
    for fname in filenames:
        if any(fname.endswith(suf) for suf in suffixes):
            path = os.path.join(dirpath, fname)
            try:
                df = pd.read_csv(path)
            except Exception as e:
                continue

            # Drop any column whose name starts with "Unnamed"
            df = df.loc[:, ~df.columns.str.startswith('Unnamed')]

            # Overwrite the CSV without the dropped columns
            df.to_csv(path, index=False)


# In[28]:


df = pd.read_csv('Final_id_data_all.csv')


# In[29]:


id_of_match_for_fill = match_id_for_prediction


# In[30]:


def copy_common_columns_by_date(source_path, target_path, date):
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


# In[31]:


def zero_specific_columns_by_date(target_path, date, data_type):
    input_date = pd.to_datetime(date).normalize()

    df = pd.read_csv(target_path, parse_dates=['Start Date'])
    df['Start Date'] = df['Start Date'].dt.normalize()

    # Define columns by data type
    bat_cols = ["Runs", "Mins", "BF", "4s", "6s", "SR", "Pos", "FantasyPoints"]
    bowl_cols = ["Overs", "BPO", "Mdns", "Runs", "Wkts", "Econ", "Pos", "FantasyPoints"]
    field_cols = ["Dis", "Ct", "St", "Ct Wk", "Ct Fi", "Catch Points", "Catch Bonus", "Stumping Points", "FantasyPoints"]

    type_to_cols = {
        "bat": bat_cols,
        "bowl": bowl_cols,
        "field": field_cols
    }

    if data_type not in type_to_cols:
        return

    cols_to_zero = [col for col in type_to_cols[data_type] if col in df.columns]

    # Apply zeroing for the specific date row
    mask = df['Start Date'] == input_date
    if not mask.any():
        return

    df.loc[mask, cols_to_zero] = 0
    df.to_csv(target_path, index=False)

import csv

url = "https://www.cricbuzz.com/cricket-series/9237/indian-premier-league-2025/matches"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/122.0.0.0 Safari/537.36"
}
timeout=40
max_retries = 15
attempt = 0

while attempt < max_retries:
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        break  # Exit the loop if successful
    except Exception as e:
        attempt += 1
    time.sleep(2)  # Optional delay between retries
# response = requests.get(url, headers=headers)
soup = BeautifulSoup(response.text, "html.parser")

match_blocks = soup.find_all("div", class_="cb-col-75 cb-col")

data = []

for block in match_blocks:
    # Match title
    title_span = block.find("span")
    match_title = title_span.text.strip() if title_span else "N/A"

    # Venue
    venue_div = block.find("div", class_="text-gray")
    venue = venue_div.text.strip() if venue_div else "N/A"

    # Result
    result_a = block.find("a", class_="cb-text-complete")
    result = result_a.text.strip() if result_a else "N/A"

    # Time block (for raw local/GMT time)
    time_div = block.find("div", class_="cb-font-12 text-gray")
    time_str = time_div.text.strip() if time_div else "N/A"

    # Timestamp to datetime conversion
    timestamp_span = block.find("span", attrs={"timestamp": True})
    if timestamp_span and timestamp_span.has_attr("timestamp"):
        timestamp_ms = int(timestamp_span["timestamp"])
        dt = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc).replace(tzinfo=None)
        date = dt.strftime('%Y-%m-%d %A %I:%M %p')
    else:
        date = "N/A"

    data.append([match_title, venue, result, date, time_str])

# Write to CSV
with open("ipl_2025_matches.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["Match Title", "Venue", "Result", "Date (UTC)", "Raw Time (GMT/Local)"])
    writer.writerows(data)

import pandas as pd

# Load your CSV
df = pd.read_csv("ipl_2025_matches.csv")

# 1. Extract the digits immediately followed by “st/nd/rd/th Match”
df['Match Number'] = df['Match Title']\
    .str.extract(r'(\d+)(?=st Match|nd Match|rd Match|th Match)', expand=False)

# 2) Assign special playoff numbers
special_map = {
    'Qualifier 1': 71,
    'Eliminator':   72,
    'Qualifier 2': 73,
    'Final':       74
}
for keyword, num in special_map.items():
    mask = df['Match Title'].str.contains(keyword)
    df.loc[mask, 'Match Number'] = num

    
# 2. Drop rows where that pattern wasn’t found
df = df.dropna(subset=['Match Number'])

# 3. Convert to int and sort
df['Match Number'] = df['Match Number'].astype(int)
df = df.sort_values('Match Number').reset_index(drop=True)

df['Date'] = (
    pd.to_datetime(df['Date (UTC)'].str.split().str[0], format='%Y-%m-%d')
      .dt.strftime('%d-%m-%Y')
)

# Save back to CSV
df.to_csv("ipl_2025_matches_corrected.csv", index=False)

# print("saved to 'ipl_2025_matches_corrected.csv'")
df[['Match Number','Date']].to_csv("ipl_match_dates.csv",index=False)

def ff_to_avoid_111(id_of_match_for_fill):
    # --- prepare your lookups once ---
    id_of_players_df = pd.read_csv("Final_id_data_all.csv")
    name_to_id = id_of_players_df.set_index("Player Name")["PlayerID"].to_dict()

    matches_dates = pd.read_csv("ipl_match_dates.csv")
    # parse dates once into datetime.date
    matches_dates["Date"] = pd.to_datetime(matches_dates["Date"],format="%d-%m-%Y").dt.date
    match_date_dict = matches_dates.set_index("Match Number")["Date"].to_dict()

    workbook_path1 = "data/SquadPlayerNames_IndianT20League.xlsx"
    excel_file1 = pd.ExcelFile(workbook_path1)  # loads just the metadata
    # loop through each match
    for i in range(1, id_of_match_for_fill):
        sheet = f"Match_{i}"
    
        # skip if the sheet isn't in this workbook
        if sheet not in excel_file1.sheet_names:
            continue
        
        # 1) load squad sheet
        squad = pd.read_excel(
            "data/SquadPlayerNames_IndianT20League.xlsx",
            sheet_name=f"Match_{i}"
        )

        # 2) find the playing players
        playing = squad[squad['IsPlaying'] == 'PLAYING']

        # 3) build per-team partner maps
        bat_partner_map  = {}
        bowl_partner_map = {}

        # 4) match date
        date_of_match = match_date_dict.get(i)  # this is a datetime.date


        for team in playing['Team'].unique():
            team_playing = playing[playing['Team'] == team]

            # --- find a valid BAT partner ---
            bat_partner_id = None
            bat_rows = team_playing[team_playing['Player Type'] == 'BAT']
            for _, bat_row in bat_rows.iterrows():

                pid = name_to_id.get(bat_row['Player Name'])
                if pid is None:
                    continue

                bat_path = os.path.join("Data_players", str(pid), f"{pid}_bat.csv")
                if not os.path.exists(bat_path):
                    continue
                try:
                    df_bat = pd.read_csv(bat_path, parse_dates=['Start Date'])
                except Exception:
                    continue
                # check for at least one matching date
                if (df_bat['Start Date'].dt.date == date_of_match).any():
                    bat_partner_id = pid
                    break
            bat_partner_map[team] = bat_partner_id

            # --- find a valid BOWL partner ---
            bowl_partner_id = None
            bowl_rows = team_playing[team_playing['Player Type'] == 'BOWL']
            for _, bowl_row in bowl_rows.iterrows():
                pid = name_to_id.get(bowl_row['Player Name'])
                if pid is None:
                    continue
                bowl_path = os.path.join("Data_players", str(pid), f"{pid}_bowl.csv")
                if not os.path.exists(bowl_path):
                    continue
                try:
                    df_bowl = pd.read_csv(bowl_path, parse_dates=['Start Date'])
                except Exception:
                    continue
                if (df_bowl['Start Date'].dt.date == date_of_match).any():
                    bowl_partner_id = pid
                    break
            bowl_partner_map[team] = bowl_partner_id

        # 5) loop through substitutes + not playing
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

            # decide which files to “fill”
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
                csv_path = os.path.join("Data_players", str(sub_id), f"{sub_id}_{ftype}.csv")
                if not os.path.exists(csv_path):
                    continue
                part_source_path = os.path.join(
                    "Data_players", str(partner_id), f"{partner_id}_{ftype}.csv"
                )
                added = copy_common_columns_by_date(part_source_path, csv_path, date_of_match)
                if added:
                    zero_specific_columns_by_date(csv_path, date_of_match, ftype)


# In[34]:


ff_to_avoid_111(match_id_for_prediction)

# In[4]:

baseurl1 = 'https://api.cricapi.com/v1/series_info?'

def get_series_info(apikey, id):
    url = f"{baseurl1}apikey={apikey}&id={id}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to retrieve data: {response.status_code}")

# API credentials
apikey = "fd3c5552-00fe-4031-90b8-749af2a69d78"
id = "d5a498c8-7596-4b93-8ab0-e0efc3345312"

# Get series match list
ipl_matches = get_series_info(apikey, id)
ipl_matches_list = ipl_matches['data']['matchList']

# In[5]:

def get_match_id(ipl_matches_list, date, x_vs_y):
    check = False
    date = datetime.strptime(date, "%d-%m-%Y")
    
    for match in ipl_matches_list:
        match_name = match['name']
        match_date = match['date']
        name = match_name.split(",")[0]
        match_date = datetime.strptime(match_date, "%Y-%m-%d")
        

        # print(name)
        # print(x_vs_y)
        # print(date)
        # print(match_date)
        
        if(x_vs_y == name and date==match_date):
            check = True
            return match["id"]

    if(check == False):
        return None
        
# print(get_match_id(ipl_matches_list,"17-05-2025","Royal Challengers Bengaluru vs Kolkata Knight Riders"))

df_mat = pd.read_csv("ipl_2025_matches_corrected.csv")

# match_id_for_prediction = "58"

match_num = int(match_id_for_prediction)

row = df_mat.loc[df_mat['Match Number'] == match_num].iloc[0]

# 2. Pull out the fields into variables
mat_name  = row['Match Title']
mat_name = mat_name.split(',', 1)[0]
mat_venue = row['Venue']
mat_date  = row['Date']

# now you can use mat_name, mat_venue, mat_date
# type(mat_date)
# print(mat_name)

ipl_match_id = get_match_id(ipl_matches_list,mat_date,mat_name)

# Fetch match info url
if ipl_match_id is not None:
    baseurl2 = 'https://api.cricapi.com/v1/match_info?'
    
    def get_match_info(apikey , id):
        url = f"{baseurl2}apikey={apikey}&id={id}"
        response = requests.get(url)
        if(response.status_code == 200):
            return response.json()
        else:
            return f'Failed to retrieve data{response}'
    nn=2
    while nn:
        match_info = get_match_info(apikey, ipl_match_id)
        nn-=1
        if 'tossWinner' in match_info['data']:
            break
        else:
            time.sleep(21)
    
    if 'tossWinner' not in match_info['data']:
        first_team = match_info['data']['name'].split(" vs ")[0]
        match_info['data']['tossWinner']=first_team
        match_info['data']['tossChoice']='bat'
    
    cut_date = match_info['data']['date']
    cut_date = pd.to_datetime(cut_date)
else:
    first_team = mat_name.split(" vs ")[0]
    match_info = { 'data': {} }
    match_info['data']['tossWinner']=first_team
    match_info['data']['tossChoice']='bat'
    match_info['data']['venue']=mat_venue
    match_info['data']['date']=mat_date
    dt12 = datetime.strptime(match_info['data']['date'], '%d-%m-%Y')
    match_info['data']['date'] = dt12.strftime('%Y-%m-%d')
    cut_date = match_info['data']['date']
    cut_date = pd.to_datetime(cut_date)


number = str(match_id_for_prediction)
base_dir = 'Data_players'
file_types = ['bat']

def compute_ground_features(df):
    ground_features = []
    past_rows = []

    for i in range(len(df)):
        row = df.iloc[i]
        ground = row['Ground']
        match_date = row['Start Date']

        # Explicit columns to ensure DataFrame integrity
        # expected_columns = ['Start Date', 'Ground', 'Runs', 'BF', '4s', '6s', 'FantasyPoints']
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
# Main processing logic
def process_file(filepath):
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
    # thresholds 10,20,…,100
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
    # rolling‐mean SR over previous 3,5,7,10 matches
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
    # (optionally) drop the helper SR column
    df_2023.drop(columns=['SR1'], inplace=True)
        # … after you've ensured df_2023['Runs'] and df_2023['BF'] exist …
    # shift so current match isn't included
    runs_shifted = df_2023['Runs'].shift(1)
    bf_shifted   = df_2023['BF'].shift(1)
    # zero‐out any innings with BF ≤ 10
    runs_masked = runs_shifted.where(bf_shifted > 10, 0)
    bf_masked   = bf_shifted.where(bf_shifted > 10,   0)
    for w in [3, 5]:
        # sum only the valid runs and balls over the window
        runs_sum = runs_masked.rolling(w).sum()
        bf_sum   = bf_masked.rolling(w).sum()
        # compute SR%; if bf_sum is 0, set SR to 0
        df_2023[f'SR_ratio_{w}'] = np.where(bf_sum == 0, 0, (runs_sum / bf_sum * 100).fillna(0))

    # Drop rows with NaN values (from shifting and rolling windows)
    # return df_2023.dropna()
    df= df_2023.dropna()
    venue_features_df = compute_ground_features(df)
    return pd.concat([df.reset_index(drop=True), venue_features_df], axis=1)


# In[8]:


# Process all player files
for player_folder in os.listdir(base_dir):
    player_path = os.path.join(base_dir, player_folder)
    if os.path.isdir(player_path):
        for ftype in file_types:
            filename = f"{player_folder}_{ftype}.csv"
            filepath = os.path.join(player_path, filename)
            if os.path.exists(filepath):
                result_df = process_file(filepath)
                if result_df is not None:
                    out_path = os.path.join(player_path, f"{player_folder}features{ftype}.csv")
                    result_df.to_csv(out_path, index=False)


# In[9]:

# In[9]:


import os
import pandas as pd

# Directory where all player folders are located
base_dir = 'Data_players'

# File types to merge
file_types = ['bat']

# Initialize merged DataFrames for each file type
merged_dfs = {ftype: [] for ftype in file_types}

# Loop through each player folder
for player_folder in os.listdir(base_dir):
    player_path = os.path.join(base_dir, player_folder)
    if os.path.isdir(player_path):
        for ftype in file_types:
            file_name = f"{player_folder}features{ftype}.csv"
            file_path = os.path.join(player_path, file_name)
            if os.path.exists(file_path):
                df = pd.read_csv(file_path)
                df['PlayerID'] = player_folder  # optional: add ID for tracking
                merged_dfs[ftype].append(df)

# Save merged files
for ftype, df_list in merged_dfs.items():
    if df_list:  # only save if we have data
        # Exclude empty or all-NA DataFrames from the list
        clean_df_list = [df for df in df_list if not df.empty and not df.isna().all().all()]

        merged = pd.concat(clean_df_list, ignore_index=True)
        for col in merged.select_dtypes(include='number').columns:
            merged[col] = merged[col].astype(float).round(1)
        merged.to_csv(f"merged_bat_bhav.csv", index=False)


# In[10]:


base_dir = 'Data_players'
file_types = ['bowl']

def convert_overs_to_balls(over):
    try:
        over_str = str(over)
        if '.' in over_str:
            parts = over_str.split('.')
            complete_overs = int(parts[0])
            extra_balls = int(parts[1])
        else:
            complete_overs = int(over_str)
            extra_balls = 0
        return complete_overs * 6 + extra_balls
    except:
        return None

def compute_ground_bowling_features(df):
    ground_features = []
    past_rows = []

    for i in range(len(df)):
        row = df.iloc[i]
        ground = row['Ground']
        match_date = row['Start Date']

        # expected_cols = ['Start Date', 'Ground', 'Overs', 'Mdns', 'Inns', 'Runs', 'Wkts', 'Econ', 'FantasyPoints', 'Balls']
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

def process_file(file_path):
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

    venue_features_df = compute_ground_bowling_features(df_2023)
    return pd.concat([df_2023, venue_features_df], axis=1).reset_index(drop=True)


# In[11]:


for player_folder in os.listdir(base_dir):
    player_path = os.path.join(base_dir, player_folder)
    if os.path.isdir(player_path):
        for ftype in file_types:
            filename = f"{player_folder}_{ftype}.csv"
            filepath = os.path.join(player_path, filename)
            if os.path.exists(filepath):
                result_df = process_file(filepath)
                if result_df is not None:
                    out_path = os.path.join(player_path, f"{player_folder}features{ftype}.csv")
                    result_df.to_csv(out_path, index=False)


# In[12]:


# Directory where all player folders are located
base_dir = 'Data_players'

# File types to merge
file_types = ['bowl']

# Initialize merged DataFrames for each file type
merged_dfs = {ftype: [] for ftype in file_types}

# Loop through each player folder
for player_folder in os.listdir(base_dir):
    player_path = os.path.join(base_dir, player_folder)
    if os.path.isdir(player_path):
        for ftype in file_types:
            file_name = f"{player_folder}features{ftype}.csv"
            file_path = os.path.join(player_path, file_name)
            if os.path.exists(file_path):
                df = pd.read_csv(file_path)
                df['PlayerID'] = player_folder  # optional: add ID for tracking
                merged_dfs[ftype].append(df)

for ftype, df_list in merged_dfs.items():
    if df_list:  # only save if we have data
        # Drop all-NaN columns in each df before merging to avoid FutureWarning
        cleaned_dfs = [df.dropna(axis=1, how='all') for df in df_list if not df.empty]

        if cleaned_dfs:  # double-check we still have data
            merged = pd.concat(cleaned_dfs, ignore_index=True)
            for col in merged.select_dtypes(include='number').columns:
                merged[col] = merged[col].astype(float).round(1)
            merged.to_csv(f"merged_{ftype}_bhav.csv", index=False)


# In[13]:


def convert_overs_to_balls(over):
    try:
        over_str = str(over)
        if '.' in over_str:
            parts = over_str.split('.')
            complete_overs = int(parts[0])
            extra_balls = int(parts[1])
        else:
            complete_overs = int(over_str)
            extra_balls = 0
        return complete_overs * 6 + extra_balls
    except:
        return None

def compute_ground_bowling_features(df):
    ground_features = []
    past_rows = []

    for i in range(len(df)):
        row = df.iloc[i]
        ground = row['Ground']
        match_date = row['Start Date']

        # expected_cols = ['Start Date', 'Ground', 'Overs', 'Mdns', 'Inns', 'Runs', 'Wkts', 'Econ', 'FantasyPoints', 'Balls']
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

def process_file_bowl(file_path):
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

    # venue_features_df = compute_ground_bowling_features(df_2023)
    return df_2023


# In[14]:


base_dir = 'Data_players'
file_types = ['bat']

def compute_ground_features_bat(df):
    ground_features = []
    past_rows = []

    for i in range(len(df)):
        row = df.iloc[i]
        ground = row['Ground']
        match_date = row['Start Date']

        # Explicit columns to ensure DataFrame integrity
        # expected_columns = ['Start Date', 'Ground', 'Runs', 'BF', '4s', '6s', 'FantasyPoints']
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
# Main processing logic
def process_file_bat(filepath):
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
    # thresholds 10,20,…,100
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
    # rolling‐mean SR over previous 3,5,7,10 matches
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
    # (optionally) drop the helper SR column
    df_2023.drop(columns=['SR1'], inplace=True)
        # … after you've ensured df_2023['Runs'] and df_2023['BF'] exist …
    # shift so current match isn't included
    runs_shifted = df_2023['Runs'].shift(1)
    bf_shifted   = df_2023['BF'].shift(1)
    # zero‐out any innings with BF ≤ 10
    runs_masked = runs_shifted.where(bf_shifted > 10, 0)
    bf_masked   = bf_shifted.where(bf_shifted > 10,   0)
    for w in [3, 5]:
        # sum only the valid runs and balls over the window
        runs_sum = runs_masked.rolling(w).sum()
        bf_sum   = bf_masked.rolling(w).sum()
        # compute SR%; if bf_sum is 0, set SR to 0
        df_2023[f'SR_ratio_{w}'] = (runs_sum / bf_sum * 100).fillna(0)
    # Drop rows with NaN values (from shifting and rolling windows)
    # return df_2023.dropna()
    df= df_2023.dropna()
    # venue_features_df = compute_ground_features_bat(df)
    return df.reset_index(drop=True)


# In[15]:


players_with_both_data = set()
players_with_bat_data = set()
players_with_bowl_data = set()

base_dir = 'Data_players'

# First pass: identify players with both types of data
for player_folder in os.listdir(base_dir):
    player_path = os.path.join(base_dir, player_folder)
    if os.path.isdir(player_path):
        # Check for batting data
        bat_filename = f"{player_folder}_bat.csv"
        bat_filepath = os.path.join(player_path, bat_filename)
        has_bat_data = os.path.exists(bat_filepath)

        # Check for bowling data
        bowl_filename = f"{player_folder}_bowl.csv"
        bowl_filepath = os.path.join(player_path, bowl_filename)
        has_bowl_data = os.path.exists(bowl_filepath)

        # Add to appropriate sets
        if has_bat_data:
            players_with_bat_data.add(player_folder)
        if has_bowl_data:
            players_with_bowl_data.add(player_folder)
        if has_bat_data and has_bowl_data:
            players_with_both_data.add(player_folder)


# Second pass: process and merge data for players with both types
for player_folder in players_with_both_data:
    player_path = os.path.join(base_dir, player_folder)

    # Process batting data
    bat_filename = f"{player_folder}_bat.csv"
    bat_filepath = os.path.join(player_path, bat_filename)
    bat_df = process_file_bat(bat_filepath)

    # Process bowling data
    bowl_filename = f"{player_folder}_bowl.csv"
    bowl_filepath = os.path.join(player_path, bowl_filename)
    bowl_df = process_file_bowl(bowl_filepath)

    if bat_df is not None and bowl_df is not None:
        # Save processed batting data
        bat_out_path = os.path.join(player_path, f"{player_folder}featuresbat1.csv")
        bat_df.to_csv(bat_out_path, index=False)

        # Save processed bowling data
        bowl_out_path = os.path.join(player_path, f"{player_folder}featuresbowl1.csv")
        bowl_df.to_csv(bowl_out_path, index=False)

        # Merge on Start Date and Ground to handle same-day matches properly
        # We now use separate BatInns and BowlInns columns
        common_cols = ['Start Date', 'Ground']

        # Add 'bat_' prefix to batting columns except common ones
        bat_cols = [col for col in bat_df.columns if col not in common_cols]
        bat_df_prefixed = bat_df.copy()
        for col in bat_cols:
            bat_df_prefixed.rename(columns={col: f'bat_{col}'}, inplace=True)

        # Add 'bowl_' prefix to bowling columns except common ones
        bowl_cols = [col for col in bowl_df.columns if col not in common_cols]
        bowl_df_prefixed = bowl_df.copy()
        for col in bowl_cols:
            bowl_df_prefixed.rename(columns={col: f'bowl_{col}'}, inplace=True)

        # Merge on Start Date and Ground (but not innings, since we want to merge same-day matches)
        combined_df = pd.merge(
            bat_df_prefixed,
            bowl_df_prefixed,
            on=common_cols,
            how='outer',
            suffixes=('_bat', '_bowl')
        )

        # Add player ID
        combined_df['PlayerID'] = player_folder

        # Save combined data
        combined_out_path = os.path.join(player_path, f"{player_folder}features_combined.csv")
        combined_df.to_csv(combined_out_path, index=False)

# Create master merged files
combined_dfs = []
bat_dfs = []
bowl_dfs = []

for player_folder in os.listdir(base_dir):
    player_path = os.path.join(base_dir, player_folder)
    if os.path.isdir(player_path):
        # Collect combined data (for players with both types)
        if player_folder in players_with_both_data:
            combined_file = f"{player_folder}features_combined.csv"
            combined_path = os.path.join(player_path, combined_file)
            if os.path.exists(combined_path):
                df = pd.read_csv(combined_path)
                combined_dfs.append(df)

        # Also collect individual batting and bowling data for separate merged files
        bat_file = f"{player_folder}featuresbat1.csv"
        bat_path = os.path.join(player_path, bat_file)
        if os.path.exists(bat_path):
            df = pd.read_csv(bat_path)
            df['PlayerID'] = player_folder
            bat_dfs.append(df)

        bowl_file = f"{player_folder}featuresbowl1.csv"
        bowl_path = os.path.join(player_path, bowl_file)
        if os.path.exists(bowl_path):
            df = pd.read_csv(bowl_path)
            df['PlayerID'] = player_folder
            bowl_dfs.append(df)

# Save the merged files
if combined_dfs:
    merged_combined = pd.concat(combined_dfs, ignore_index=True)
    for col in merged_combined.select_dtypes(include='number').columns:
        merged_combined[col] = merged_combined[col].astype(float).round(1)
    merged_combined.to_csv("merged_combined.csv", index=False)

# In[16]:


match_ground_name=match_info['data']['venue']


# In[17]:


id_of_match=number
cut_date = match_info['data']['date']


# In[18]:


cut_date = pd.to_datetime(cut_date)


# In[19]:
print("STEP 1 COMPLETE")

# Pause here before proceeding to STEP 2
wait_for_resume()

print("STEP 2 COMPLETE")

def get_match_id(ipl_matches_list,number):
    if(int(number) == 71):
        return "1c2f9a38-4c3a-407b-90c1-9b78dee63cb8"
    if(int(number) == 72):
        return "40596379-a096-4513-8b6f-41df069ca70c"
    if(int(number) == 73):
        return "08b32e61-9c96-4f37-8f76-0b3439a80567"
    if(int(number) == 74):
        return "b70371b1-6528-4af6-992c-e880ed585183"

    for match in ipl_matches_list:
        match_name = match['name']
        num = ""

        for ch in match_name:
            if(ch.isnumeric()):
                num += ch
        if(number == num and  'Qualifier' not in match_name):
            match_id = match['id']

    return match_id

number = str(match_id_for_prediction)

# Get match id
ipl_match_id = get_match_id(ipl_matches_list , number)


# Fetch match info url
baseurl2 = 'https://api.cricapi.com/v1/match_info?'

def get_match_info(apikey , id):
    url = f"{baseurl2}apikey={apikey}&id={id}"
    response = requests.get(url)
    if(response.status_code == 200):
        return response.json()
    else:
        return f'Failed to retrieve data{response}'


match_info = get_match_info(apikey, ipl_match_id)
if 'tossWinner' in match_info['data']:
    pass
else:
    print("Try after 5 mins")

if 'tossWinner' not in match_info['data']:
    first_team = match_info['data']['name'].split(" vs ")[0]
    match_info['data']['tossWinner']=first_team
    match_info['data']['tossChoice']='bat'
    

cut_date = match_info['data']['date']
cut_date = pd.to_datetime(cut_date)


id = number


# In[20]:


df = pd.read_excel("data/SquadPlayerNames_IndianT20League.xlsx",sheet_name =f"Match_{id}")


# In[21]:


id_data_1 = pd.read_csv("Final_id_data_all.csv")


# In[22]:


win_team=match_info["data"]["tossWinner"]


# In[23]:


df_gr_data= pd.read_csv("sort_gr_coun_full_name.csv")
df_gr_data = df_gr_data[["Ground Link","corr_ground","id_gr","Name_gr_ex"]]

def find_ground_info(full_name: str):
    """
    Given a full ground name, return (corr_ground, Ground Link) from df_gr_data.
    1) Try exact match (case‐insensitive) on Name_gr_ex.
    2) If none, take prefix before first comma and look for that substring.
    """
    # lowercase everything for case‐insensitive comparison
    name_l = full_name.lower().strip()

    # 1) exact match
    mask_exact = df_gr_data['Name_gr_ex'].str.lower().str.strip() == name_l
    if mask_exact.any():
        row = df_gr_data.loc[mask_exact].iloc[0]
        return row['corr_ground'], row['Ground Link']

    # 2) prefix match
    prefix = name_l.split(',', 1)[0].strip()
    mask_pref = df_gr_data['Name_gr_ex'].str.lower().str.contains(prefix, na=False)
    if mask_pref.any():
        row = df_gr_data.loc[mask_pref].iloc[0]
        return row['corr_ground'], row['Ground Link']

    # nothing found
    return None, None


# In[24]:


match_ground_for_model = find_ground_info(match_ground_name)[0]


# In[25]:


# Wikipedia URL
url = 'https://en.wikipedia.org/wiki/2025_Indian_Premier_League'

# Fetch the page
response = requests.get(url)
soup = BeautifulSoup(response.text, 'html.parser')

# Locate the points table
table = soup.find('table', class_='wikitable module-CricketLeagueGroupStageSummary')

if table is None:
    raise Exception("Points table not found. Check the class name or table structure.")

# Get all rows
rows = table.find_all('tr')

# Extract headers
for i, row in enumerate(rows):
    th_tags = row.find_all('th')
    if th_tags and len(th_tags) > 1:
        headers = [th.get_text(strip=True) for th in th_tags]
        data_rows = rows[i + 1:]
        break

# Extract table data
data = []
for row in data_rows:
    cells = row.find_all(['th', 'td'])
    row_data = [cell.get_text(strip=True) for cell in cells]
    if row_data and len(row_data) == len(headers):
        data.append(row_data)

# Create DataFrame
df = pd.DataFrame(data, columns=headers)

# Save to CSV
df.to_csv("ipl_2025_points_table.csv", index=False)


# In[26]:


df_ini_teams = pd.read_csv("ipl_2025_points_table.csv",index_col=0)


# In[27]:


team_code_map = dict(zip(df_ini_teams.index, df_ini_teams.columns))


# In[28]:


initials_of_win_team = team_code_map[win_team]
choice_of_win_team = match_info['data']['tossChoice']


# In[29]:


df = pd.read_excel("data/SquadPlayerNames_IndianT20League.xlsx",sheet_name =f"Match_{id}")


# In[30]:


def build_inns_map():
    """
    df: DataFrame with a column 'Team' containing exactly two unique team‐identifiers (either full names or initials).
    initials_of_win_team: a string, e.g. 'CSK' or 'Chennai Super Kings'
    choice_of_win_team: either 'bat' or 'bowl'

    Returns a dict mapping each team → innings number (1 or 2).
    """
    # 1) pull out the two teams
    teams = list(df['Team'].unique())
    if len(teams) != 2:
        raise ValueError(f"Expected exactly 2 unique teams, got {teams}")

    # 2) figure out which key is the winner
    if initials_of_win_team in teams:
        winner = initials_of_win_team
    else:
        # fallback: match first character
        init_char = initials_of_win_team[0].lower()
        matches = [t for t in teams if t and t[0].lower() == init_char]
        if len(matches) == 1:
            winner = matches[0]
        else:
            raise ValueError(
                f"Could not resolve winner from initials '{initials_of_win_team}' "
                f"against teams {teams}"
            )

    # 3) the other team is the loser
    loser = teams[0] if teams[1] == winner else teams[1]

    # 4) assign innings based on toss choice
    choice = choice_of_win_team.lower()
    if choice == 'bat':
        inns_map_ex = {winner: 1, loser: 2}
    elif choice == 'bowl':
        inns_map_ex = {winner: 2, loser: 1}
    else:
        raise ValueError("choice_of_win_team must be 'bat' or 'bowl'")

    return inns_map_ex


# In[31]:


inns_map_ex =build_inns_map()


# In[32]:


id_of_match = pd.DataFrame()
id_of_match["Player Name"] = df["Player Name"]
id_of_match["Team"] = df["Team"]


# In[33]:


# Map PlayerID directly using 'Player Name' as key
id_of_match["PlayerID"] = id_of_match["Player Name"].map(
    id_data_1.set_index("Player Name")["PlayerID"]
)


# In[34]:


id_of_match.dropna(inplace=True)

id_of_match["PlayerID"] = id_of_match["PlayerID"].astype(int)


# In[35]:


base_dir = 'Data_players'
root_folder = 'Data_players'
file_types = ['bat']

def compute_ground_features_pred(df,features):
    ground_history = df[df['Ground'] == match_ground_for_model]

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

def process_file_bat_pred(filepath):
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
    # fantasy = df_2023['FantasyPoints']
    features = {}

    # Window sizes for rolling calculations
    windows = [2, 3, 4, 5, 6]
    boundary_windows = [2, 4, 6]

    # Calculate rolling features for Runs (shifted)
    for window in windows:
        features[f'Mean_Run_{window}'] = df_2023['Runs'].tail(window).mean()
        features[f'Std_Run_{window}'] = df_2023['Runs'].tail(window).std()

    # Calculate rolling features for FantasyPoints (shifted)
    for window in windows:
        features[f'Mean_Fan_{window}'] = df_2023['FantasyPoints'].tail(window).mean()
        features[f'Std_Fan_{window}'] = df_2023['FantasyPoints'].tail(window).std()

    # Calculate rolling features for 4s and 6s (shifted)
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
    features = compute_ground_features_pred(df_2023,features)
    return pd.DataFrame([features])


# In[36]:


root_folder = "Data_players"
all_dfs = []

for pid in id_of_match['PlayerID']:
    csv_path = os.path.join(root_folder, str(pid), f"{pid}_bat.csv")
    if not os.path.isfile(csv_path):
        continue

    df_player = process_file_bat_pred(csv_path)
    if df_player is None or df_player.empty:
        continue

    # inject the player ID as a column
    df_player['PlayerID'] = pid
    all_dfs.append(df_player)

# concatenate into one flat DataFrame
if all_dfs:
    final_df = pd.concat(all_dfs, ignore_index=True)
else:
    final_df = pd.DataFrame()


# In[37]:


# final_df.set_index("PlayerID",inplace=True)

# In[37]:


final_df.set_index("PlayerID",inplace=True)


# In[38]:


team_map = id_of_match.set_index('PlayerID')['Team']

# 2) inject the Team into final_df (its index is PlayerID)
final_df['Team'] = final_df.index.to_series().map(team_map)

# 3) map Team → Inns using your inns_map_ex dict
final_df['Inns'] = final_df['Team'].map(inns_map_ex)

# (optional) drop the helper Team column if you don’t need it
final_df.drop(columns='Team', inplace=True)


# In[39]:


df = pd.read_csv('merged_bat_bhav.csv')


# In[40]:


df.drop(columns = ["Runs","Start Date","PlayerID","BF","4s","6s"],inplace=True)
df1 = pd.get_dummies(df, columns=['Ground'],dtype=int)

X = df1.loc[:, ~df1.columns.isin(["FantasyPoints"])]
y = df1['FantasyPoints']

X_train = X
y_train = y



model = CatBoostRegressor(
    iterations=500,
    learning_rate=0.05,
    depth=5,
    random_seed=42,
    verbose=False # ✅ force consistent results

)

model.fit(X_train, y_train)


# In[41]:


# 1) grab all df1 columns that start with "Ground_"
ground_cols = [c for c in df1.columns if c.startswith("Ground_")]

# 2) build a DataFrame of zeros with the same index as final_df
zeros_df = pd.DataFrame(
    0,
    index=final_df.index,
    columns=ground_cols
)

# 3) concatenate in one go
final_df = pd.concat([final_df, zeros_df], axis=1)


# In[42]:


final_df[f"Ground_{match_ground_for_model}"] = 1


# In[43]:


preds = model.predict(final_df)
# build res_df_fan with the same index as final_df
res_df_fan = pd.DataFrame(
    preds,
    index=final_df.index,
    columns=['PredictedFantasyPoints']
)

name_map = id_of_match.set_index('PlayerID')['Player Name']

# if res_df_fan doesn’t already have PlayerID, grab it from final_df
# res_df_fan['PlayerID'] = final_df['PlayerID']

# map names
res_df_fan['Player Name'] = res_df_fan.index.map(name_map)

# reorder columns if you like
res_df_fan = res_df_fan[['Player Name', 'PredictedFantasyPoints']]


# In[44]:


df = pd.read_excel("data/SquadPlayerNames_IndianT20League.xlsx",sheet_name =f"Match_{id}")


# In[45]:


id_data_1 = pd.read_csv("Final_id_data_all.csv")


# In[46]:


win_team=match_info["data"]["tossWinner"]


# In[47]:


df_gr_data= pd.read_csv("sort_gr_coun_full_name.csv")
df_gr_data = df_gr_data[["Ground Link","corr_ground","id_gr","Name_gr_ex"]]

def find_ground_info(full_name: str):
    """
    Given a full ground name, return (corr_ground, Ground Link) from df_gr_data.
    1) Try exact match (case‐insensitive) on Name_gr_ex.
    2) If none, take prefix before first comma and look for that substring.
    """
    # lowercase everything for case‐insensitive comparison
    name_l = full_name.lower().strip()

    # 1) exact match
    mask_exact = df_gr_data['Name_gr_ex'].str.lower().str.strip() == name_l
    if mask_exact.any():
        row = df_gr_data.loc[mask_exact].iloc[0]
        return row['corr_ground'], row['Ground Link']

    # 2) prefix match
    prefix = name_l.split(',', 1)[0].strip()
    mask_pref = df_gr_data['Name_gr_ex'].str.lower().str.contains(prefix, na=False)
    if mask_pref.any():
        row = df_gr_data.loc[mask_pref].iloc[0]
        return row['corr_ground'], row['Ground Link']

    # nothing found
    return None, None


# In[48]:


match_ground_for_model = find_ground_info(match_ground_name)[0]


# In[49]:


df_ini_teams = pd.read_csv("ipl_2025_points_table.csv",index_col=0)
team_code_map = dict(zip(df_ini_teams.index, df_ini_teams.columns))


# In[50]:


initials_of_win_team = team_code_map[win_team]
choice_of_win_team = match_info['data']['tossChoice']


# In[51]:


def build_inns_map():
    """
    df: DataFrame with a column 'Team' containing exactly two unique team‐identifiers (either full names or initials).
    initials_of_win_team: a string, e.g. 'CSK' or 'Chennai Super Kings'
    choice_of_win_team: either 'bat' or 'bowl'

    Returns a dict mapping each team → innings number (1 or 2).
    """
    # 1) pull out the two teams
    teams = list(df['Team'].unique())
    if len(teams) != 2:
        raise ValueError(f"Expected exactly 2 unique teams, got {teams}")

    # 2) figure out which key is the winner
    if initials_of_win_team in teams:
        winner = initials_of_win_team
    else:
        # fallback: match first character
        init_char = initials_of_win_team[0].lower()
        matches = [t for t in teams if t and t[0].lower() == init_char]
        if len(matches) == 1:
            winner = matches[0]
        else:
            raise ValueError(
                f"Could not resolve winner from initials '{initials_of_win_team}' "
                f"against teams {teams}"
            )

    # 3) the other team is the loser
    loser = teams[0] if teams[1] == winner else teams[1]

    # 4) assign innings based on toss choice
    choice = choice_of_win_team.lower()
    if choice == 'bat':
        inns_map_ex = {winner: 2, loser: 1}
    elif choice == 'bowl':
        inns_map_ex = {winner: 1, loser: 2}
    else:
        raise ValueError("choice_of_win_team must be 'bat' or 'bowl'")

    return inns_map_ex


# In[52]:


inns_map_ex =build_inns_map()


# In[53]:


id_of_match = pd.DataFrame()
id_of_match["Player Name"] = df["Player Name"]
id_of_match["Team"] = df["Team"]


# In[54]:


# Map PlayerID directly using 'Player Name' as key
id_of_match["PlayerID"] = id_of_match["Player Name"].map(
    id_data_1.set_index("Player Name")["PlayerID"]
)


# In[55]:


id_of_match.dropna(inplace=True)

id_of_match["PlayerID"] = id_of_match["PlayerID"].astype(int)


# In[56]:


root_folder="Data_players"
base_dir = 'Data_players'

# File types to process
file_types=['bowl']


# In[57]:


def convert_overs_to_balls(over):
    """
    Convert cricket overs notation (e.g., 3.4 means 3 overs and 4 balls)
    to the total number of balls bowled.
    """
    try:
        over_str = str(over)
        if '.' in over_str:
            parts = over_str.split('.')
            complete_overs = int(parts[0])
            extra_balls = int(parts[1])
        else:
            complete_overs = int(over_str)
            extra_balls = 0
        return complete_overs * 6 + extra_balls
    except Exception as e:
        return None


def compute_ground_bowling_features_pred(features,df):
    ground_history = df[df['Ground']==match_ground_for_model]

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

def process_file_bowl_pred(file_path):
    # Read file and strip whitespace from column names
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
    # df_2023['Balls'] = df_2023['Overs'].apply(convert_overs_to_balls)
    df_2023.loc[:, 'Balls'] = df_2023['Overs'].apply(convert_overs_to_balls)

    # Fill missing values for Runs conceded with 0
    df_2023['Runs'] = df_2023['Runs'].fillna(0)
    df_2023['Wkts'] = df_2023['Wkts'].fillna(0)
    # Rolling windows for various calculations
    features = {}
    windows = [2, 3, 4, 5, 6]
    # return df_2023
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

    # Rolling Weighted Economy Rate:
    # Sum of runs conceded over the window divided by the sum of balls bowled (converted to overs)
    for w in [3, 5]:
        runs_sum = df_2023['Runs'].tail(w).sum()
        balls_sum = df_2023['Balls'].tail(w).sum()
        # Avoid division by zero by filling or replacing zeros with NaN before calculation then back-filling zeros
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

    # Rolling Fantasy Efficiency:
    # Rolling sum of FantasyPoints divided by rolling sum of Balls bowled
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
        # If no wickets taken, set strike rate to a high value (e.g., 999)
        if wkts_sum==0:
            features[f'Strike_Rate_{w}'] = 999
        else:
            features[f'Strike_Rate_{w}'] = (balls_sum / (wkts_sum))

    df = df.sort_values('Start Date')
    df = df[df['Start Date'] < cut_date]
    df_2023 = df[df['Start Date'].dt.year >= 2023]
    df_2023.loc[:, 'Balls'] = df_2023['Overs'].apply(convert_overs_to_balls)
    df_2023 = df_2023[['Start Date','Balls','Ground', 'Overs', 'Mdns', 'Inns','Wkts', 'Runs', 'Econ', 'FantasyPoints']].copy()
    features = compute_ground_bowling_features_pred(features,df_2023)
    # Drop rows with NaN values resulting from shifting and rolling
    return pd.DataFrame([features])


# In[58]:


root_folder = "Data_players"
all_dfs = []

for pid in id_of_match['PlayerID']:
    csv_path = os.path.join(root_folder, str(pid), f"{pid}_bowl.csv")
    if not os.path.isfile(csv_path):
        continue

    df_player = process_file_bowl_pred(csv_path)
    if df_player is None or df_player.empty:
        continue

    # inject the player ID as a column
    df_player['PlayerID'] = pid
    all_dfs.append(df_player)

# concatenate into one flat DataFrame
if all_dfs:
    final_df = pd.concat(all_dfs, ignore_index=True)
else:
    final_df = pd.DataFrame()


# In[59]:


final_df.set_index("PlayerID",inplace=True)


# In[60]:


team_map = id_of_match.set_index('PlayerID')['Team']

# 2) inject the Team into final_df (its index is PlayerID)
final_df['Team'] = final_df.index.to_series().map(team_map)

# 3) map Team → Inns using your inns_map_ex dict
final_df['Inns'] = final_df['Team'].map(inns_map_ex)

# (optional) drop the helper Team column if you don’t need it
final_df.drop(columns='Team', inplace=True)


# In[61]:


df = pd.read_csv('merged_bowl_bhav.csv')


# In[62]:


df.drop(columns = ["Pos","BPO","Runs","Opposition","PlayerID","Ground Link","match_id","Overs","Team Link","Mdns","Econ","Balls","Start Date","Wkts"],inplace=True)
df.rename(columns = {"BowlInns":"Inns"},inplace=True)


# In[63]:


df1 = pd.get_dummies(df, columns=['Ground'],dtype=int,drop_first=True)


# In[64]:


X = df1.loc[:, ~df1.columns.isin(["FantasyPoints"])]
y = df1['FantasyPoints']

X_train = X
y_train = y


model = CatBoostRegressor(
    iterations=500,
    learning_rate=0.05,
    depth=5,
    random_seed=42,
    verbose=False  # ✅ force consistent results

)

model.fit(X_train, y_train)


# In[65]:


# 1) grab all df1 columns that start with "Ground_"
ground_cols = [c for c in df1.columns if c.startswith("Ground_")]

# 2) build a DataFrame of zeros with the same index as final_df
zeros_df = pd.DataFrame(
    0,
    index=final_df.index,
    columns=ground_cols
)

# 3) concatenate in one go
final_df = pd.concat([final_df, zeros_df], axis=1)


# In[66]:


final_df[f"Ground_{match_ground_for_model}"] = 1


# In[67]:


preds = model.predict(final_df)
# build res_df_fan_bowl with the same index as final_df
res_df_fan_bowl = pd.DataFrame(
    preds,
    index=final_df.index,
    columns=['PredictedFantasyPoints']
)

name_map = id_of_match.set_index('PlayerID')['Player Name']

# if res_df_fan_bowl doesn’t already have PlayerID, grab it from final_df
# res_df_fan_bowl['PlayerID'] = final_df['PlayerID']

# map names
res_df_fan_bowl['Player Name'] = res_df_fan_bowl.index.map(name_map)

# reorder columns if you like
res_df_fan_bowl = res_df_fan_bowl[['Player Name', 'PredictedFantasyPoints']]


# In[68]:


match_ground_name=match_info['data']['venue']


# In[69]:


id_of_match=number
cut_date = match_info['data']['date']
cut_date = pd.to_datetime(cut_date)


# In[70]:


id = number


# In[71]:


df = pd.read_excel("data/SquadPlayerNames_IndianT20League.xlsx",sheet_name =f"Match_{id}")


# In[72]:


id_data_1 = pd.read_csv("Final_id_data_all.csv")


# In[73]:


win_team=match_info["data"]["tossWinner"]


# In[74]:


df_gr_data= pd.read_csv("sort_gr_coun_full_name.csv")
df_gr_data = df_gr_data[["Ground Link","corr_ground","id_gr","Name_gr_ex"]]

def find_ground_info(full_name: str):
    """
    Given a full ground name, return (corr_ground, Ground Link) from df_gr_data.
    1) Try exact match (case‐insensitive) on Name_gr_ex.
    2) If none, take prefix before first comma and look for that substring.
    """
    # lowercase everything for case‐insensitive comparison
    name_l = full_name.lower().strip()

    # 1) exact match
    mask_exact = df_gr_data['Name_gr_ex'].str.lower().str.strip() == name_l
    if mask_exact.any():
        row = df_gr_data.loc[mask_exact].iloc[0]
        return row['corr_ground'], row['Ground Link']

    # 2) prefix match
    prefix = name_l.split(',', 1)[0].strip()
    mask_pref = df_gr_data['Name_gr_ex'].str.lower().str.contains(prefix, na=False)
    if mask_pref.any():
        row = df_gr_data.loc[mask_pref].iloc[0]
        return row['corr_ground'], row['Ground Link']

    # nothing found
    return None, None


# In[75]:


match_ground_for_model = find_ground_info(match_ground_name)[0]


# In[76]:


df_ini_teams = pd.read_csv("ipl_2025_points_table.csv",index_col=0)
team_code_map = dict(zip(df_ini_teams.index, df_ini_teams.columns))


# In[77]:


initials_of_win_team = team_code_map[win_team]
choice_of_win_team = match_info['data']['tossChoice']


# In[78]:


def build_inns_map():
    """
    df: DataFrame with a column 'Team' containing exactly two unique team‐identifiers (either full names or initials).
    initials_of_win_team: a string, e.g. 'CSK' or 'Chennai Super Kings'
    choice_of_win_team: either 'bat' or 'bowl'

    Returns a dict mapping each team → innings number (1 or 2).
    """
    # 1) pull out the two teams
    teams = list(df['Team'].unique())
    if len(teams) != 2:
        raise ValueError(f"Expected exactly 2 unique teams, got {teams}")

    # 2) figure out which key is the winner
    if initials_of_win_team in teams:
        winner = initials_of_win_team
    else:
        # fallback: match first character
        init_char = initials_of_win_team[0].lower()
        matches = [t for t in teams if t and t[0].lower() == init_char]
        if len(matches) == 1:
            winner = matches[0]
        else:
            raise ValueError(
                f"Could not resolve winner from initials '{initials_of_win_team}' "
                f"against teams {teams}"
            )

    # 3) the other team is the loser
    loser = teams[0] if teams[1] == winner else teams[1]

    # 4) assign innings based on toss choice
    choice = choice_of_win_team.lower()
    if choice == 'bat':
        inns_map_ex = {winner: 1, loser: 2}
    elif choice == 'bowl':
        inns_map_ex = {winner: 2, loser: 1}
    else:
        raise ValueError("choice_of_win_team must be 'bat' or 'bowl'")

    return inns_map_ex


# In[79]:


inns_map_ex =build_inns_map()


# In[80]:


id_of_match = pd.DataFrame()
id_of_match["Player Name"] = df["Player Name"]
id_of_match["Team"] = df["Team"]


# In[81]:


id_of_match["PlayerID"] = id_of_match["Player Name"].map(
    id_data_1.set_index("Player Name")["PlayerID"]
)


# In[82]:


id_of_match.dropna(inplace=True)

id_of_match["PlayerID"] = id_of_match["PlayerID"].astype(int)


# In[83]:
def compute_ground_features_bat(df,features):

    ground_history = df[df['Ground'] == match_ground_for_model]
    if not ground_history.empty:
        for w in [2, 3, 5]:
            hist = ground_history.sort_values(by='Start Date').tail(w).copy()
            hist[['Runs', 'BF', '4s', '6s', 'FantasyPoints']] = hist[['Runs', 'BF', '4s', '6s', 'FantasyPoints']].fillna(0)

            hist['Boundaries'] = hist['4s'] + hist['6s']
            hist['SR'] = (hist['Runs'] / hist['BF']) * 100
            hist.loc[hist['BF'] <= 10, 'SR'] = 0

            for metric in ['Runs', '4s', '6s', 'Boundaries', 'FantasyPoints', 'SR']:
                features[f'bat_Ak_Ground_Mean_{metric}_{w}'] = hist[metric].mean()
                features[f'bat_Ak_Ground_Std_{metric}_{w}'] = hist[metric].std()
                if metric == '4s' or metric == '6s' or metric == 'Boundaries':
                    features[f'bat_Ak_Ground_Sum_{metric}_{w}'] = hist[metric].sum()  

            bf_sum = hist['BF'].sum()
            bd_sum = hist['Boundaries'].sum()
            features[f'bat_Ak_Ground_Boundary_Ratio_{w}'] = (bd_sum / bf_sum * 100) if bf_sum else np.nan

        # SR Ratio features
        runs_shifted = ground_history['Runs']
        bf_shifted = ground_history['BF']
        runs_masked = runs_shifted.where(bf_shifted > 10, 0)
        bf_masked = bf_shifted.where(bf_shifted > 10, 0)

        for w in [2, 3, 5]:
            runs_sum = runs_masked.tail(w).sum()
            bf_sum = bf_masked.tail(w).sum()
            sr_ratio = (runs_sum / bf_sum * 100)
            if np.isnan(sr_ratio):
                sr_ratio = 0
            features[f'bat_Ak_Ground_SR_ratio_{w}'] = sr_ratio if not np.isnan(sr_ratio) else np.nan

        # Perc_Run_gt_X features
        for threshold in range(10, 101, 10):
            perc_series = (ground_history['Runs'] > threshold).tail(5).mean() * 100
            features[f'bat_Ak_Ground_Perc_Run_gt_{threshold}_5'] = perc_series if not np.isnan(perc_series) else np.nan

    else:
        # Fill with zeros if no prior ground data
        for w in [2, 3, 5]:
            for metric in ['Runs', '4s', '6s', 'Boundaries', 'FantasyPoints', 'SR']:
                features[f'bat_Ak_Ground_Mean_{metric}_{w}'] = np.nan
                features[f'bat_Ak_Ground_Std_{metric}_{w}'] = np.nan
                if metric == '4s' or metric == '6s' or metric == 'Boundaries':
                    features[f'bat_Ak_Ground_Sum_{metric}_{w}'] = np.nan
            features[f'bat_Ak_Ground_Boundary_Ratio_{w}'] = np.nan
            features[f'bat_Ak_Ground_SR_ratio_{w}'] = np.nan

        for threshold in range(10, 101, 10):
            features[f'bat_Ak_Ground_Perc_Run_gt_{threshold}_5'] = np.nan



    return features


# In[84]:


def process_batting_file(file_path):
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

    # features_df = pd.DataFrame([features])
    # return features_df

    # features = compute_ground_features_bat(df_2023,features)
    return pd.DataFrame([features])
    # # return pd.concat([features_df.reset_index(drop=True), venue_features_df], axis=1)


# In[85]:


def convert_overs_to_balls(over):
    """
    Convert cricket overs notation (e.g., 3.4 means 3 overs and 4 balls)
    to the total number of balls bowled.
    """
    try:
        over_str = str(over)
        if '.' in over_str:
            parts = over_str.split('.')
            complete_overs = int(parts[0])
            extra_balls = int(parts[1])
        else:
            complete_overs = int(over_str)
            extra_balls = 0
        return complete_overs * 6 + extra_balls
    except Exception as e:
        return None


base_dir = 'Data_players'
file_types = ['bowl']

def convert_overs_to_balls(over):
    try:
        over_str = str(over)
        if '.' in over_str:
            parts = over_str.split('.')
            complete_overs = int(parts[0])
            extra_balls = int(parts[1])
        else:
            complete_overs = int(over_str)
            extra_balls = 0
        return complete_overs * 6 + extra_balls
    except:
        return None

def compute_ground_bowling_features(df,features):

    ground_history = df[df['Ground']==match_ground_for_model]


    if not ground_history.empty:
        for w in [2, 3, 5]:
            hist = ground_history.sort_values('Start Date').tail(w).copy()
            for col in ['Runs', 'Wkts', 'Econ', 'FantasyPoints', 'Balls']:
                features[f'bowl_Ak_Ground_Mean_{col}_{w}'] = hist[col].mean()
                features[f'bowl_Ak_Ground_Std_{col}_{w}'] = hist[col].std()

            features[f'bowl_Ak_Ground_Sum_Balls_{w}'] = hist['Balls'].sum()
            features[f'bowl_Ak_Ground_Sum_Wkts_{w}'] = hist['Wkts'].sum()

            runs_sum = hist['Runs'].sum()
            wkts_sum = hist['Wkts'].sum()
            balls_sum = hist['Balls'].sum()
            fan_sum = hist['FantasyPoints'].sum()

            features[f'bowl_Ak_Ground_Weighted_Econ_{w}'] = (runs_sum / (balls_sum / 6)) if balls_sum > 0 else np.nan
            features[f'bowl_Ak_Ground_Wkt_Rate_{w}'] = (wkts_sum / (balls_sum / 6)) if balls_sum > 0 else np.nan
            features[f'bowl_Ak_Ground_Fan_Efficiency_{w}'] = (fan_sum / balls_sum) if balls_sum > 0 else np.nan
            features[f'bowl_Ak_Ground_Strike_Rate_{w}'] = (balls_sum / wkts_sum) if wkts_sum > 0 else 99

        hist = ground_history.sort_values('Start Date').tail(5).copy()
        for threshold in range(10, 101, 10):
            run_cond = hist['Runs'] > threshold
            features[f'bowl_Ak_Ground_Perc_Run_gt_{threshold}_5'] = run_cond.mean() * 100 if len(run_cond) >= 5 else np.nan

        for threshold in [1, 2, 3, 4, 5]:
            wkt_cond = hist['Wkts'] >= threshold
            features[f'bowl_Ak_Ground_Perc_Wkts_gt_{threshold}_5'] = wkt_cond.mean() * 100 if len(wkt_cond) >= 5 else np.nan

    else:
        for w in [2, 3, 5]:
            for col in ['Runs', 'Wkts', 'Econ', 'FantasyPoints', 'Balls']:
                features[f'bowl_Ak_Ground_Mean_{col}_{w}'] = np.nan
                features[f'bowl_Ak_Ground_Std_{col}_{w}'] = np.nan
            features[f'bowl_Ak_Ground_Sum_Balls_{w}'] = np.nan
            features[f'bowl_Ak_Ground_Sum_Wkts_{w}'] = np.nan

            features[f'bowl_Ak_Ground_Weighted_Econ_{w}'] = np.nan
            features[f'bowl_Ak_Ground_Wkt_Rate_{w}'] = np.nan
            features[f'bowl_Ak_Ground_Fan_Efficiency_{w}'] = np.nan
            features[f'bowl_Ak_Ground_Strike_Rate_{w}'] = np.nan

        for threshold in range(10, 101, 10):
                features[f'bowl_Ak_Ground_Perc_Run_gt_{threshold}_5'] = np.nan
        for threshold in [1, 2, 3, 4, 5]:
                features[f'bowl_Ak_Ground_Perc_Wkts_gt_{threshold}_5'] = np.nan


    return features


# In[86]:


def process_bowling_file(file_path):
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

    # features_df = pd.DataFrame([features])
    # return features_df
    # features = compute_ground_bowling_features(df_2023,features)
    return pd.DataFrame([features])


# In[87]:


root_folder = "Data_players"
all_dfs = []

for pid in id_of_match['PlayerID']:
    csv_path_bat = os.path.join(root_folder, str(pid), f"{pid}_bat.csv")
    if not os.path.isfile(csv_path_bat):
        continue
    csv_path_bowl = os.path.join(root_folder, str(pid), f"{pid}_bowl.csv")
    if not os.path.isfile(csv_path_bowl):
        continue

    df_bat = process_batting_file(csv_path_bat)
    if df_bat is None or df_bat.empty:
        continue
    df_bowl = process_bowling_file(csv_path_bowl)
    if df_bowl is None or df_bowl.empty:
        continue

    df_player = pd.concat([df_bat, df_bowl], axis=1, ignore_index=False)
    if df_player is None or df_player.empty:
        continue

    # inject the player ID as a column
    df_player['PlayerID'] = pid
    all_dfs.append(df_player)

# concatenate into one flat DataFrame
if all_dfs:
    final_df = pd.concat(all_dfs, ignore_index=True)
else:
    final_df = pd.DataFrame()

# In[88]:


final_df.set_index("PlayerID",inplace=True)


# In[89]:


team_map = id_of_match.set_index('PlayerID')['Team']

# 2) inject the Team into final_df (its index is PlayerID)
final_df['Team'] = final_df.index.to_series().map(team_map)

# 3) map Team → Inns using your inns_map_ex dict
final_df['Inns'] = final_df['Team'].map(inns_map_ex)

# (optional) drop the helper Team column if you don’t need it
final_df.drop(columns='Team', inplace=True)


# In[90]:


df = pd.read_csv('merged_combined.csv')


# In[91]:


df = df[df.isna().sum(axis=1) <= 10]


# In[92]:


df = df[(df == 0).sum(axis=1) <= 70]


# In[93]:


df = df.rename(columns={'bat_BatInns': 'Inns'})


# In[94]:


df.fillna(0,inplace=True)


# In[95]:


ground_encoded = pd.get_dummies(df['Ground'], prefix = 'Ground')
ground_encoded = ground_encoded.astype(int)
df_without_ground = df.drop('Ground', axis=1)


# In[96]:


df_without_ground['Total_fantasy'] = df_without_ground['bat_FantasyPoints'].fillna(0) + df_without_ground['bowl_FantasyPoints'].fillna(0)
y = df_without_ground['Total_fantasy']


# In[97]:


df_without_ground = df_without_ground.drop([
    'Total_fantasy','bat_FantasyPoints', 'bowl_FantasyPoints', 'Start Date', 'PlayerID',
    'bat_Runs', 'bat_BF', 'bat_4s', 'bat_6s', 'bowl_BPO',
    'bowl_Overs', 'bowl_Mdns', 'bowl_BowlInns', 'bowl_Runs', 'bowl_Wkts',
    'bowl_Econ', 'bowl_Balls'
], axis=1)


# In[98]:


df_without_ground_common = df_without_ground.drop(['bowl_Team Link', 'bowl_Ground Link', 'bat_Std_4s_4', 'bat_Std_6s_2', 'bat_Std_4s_6', 'bat_Std_6s_6',   'bat_Std_4s_2', 'bowl_Opposition', 'bowl_match_id', 'bat_Std_Boundaries_6',  'bowl_Pos', 'bat_Std_Boundaries_4',  'bat_Std_SR_5',   'bat_Std_Boundaries_2',  'bat_Std_SR_3', 'bat_Std_6s_4'], axis = 1)
final_df_common = final_df.drop(['bowl_Mean_Econ_2', 'bowl_Mean_Econ_6', 'bowl_Mean_Econ_4', 'bowl_Std_Econ_2', 'bowl_Std_Econ_4', 'bowl_Std_Econ_6'], axis = 1)


# In[99]:


df_without_ground_common = df_without_ground_common.rename(columns={'bat_Inns': 'Inns'})


# In[100]:


df_with_ground = pd.concat([df_without_ground_common, ground_encoded], axis=1)


# In[101]:


x = df_with_ground


# In[102]:


X_train = x
y_train = y

model = CatBoostRegressor(
    iterations=500,
    learning_rate=0.05,
    depth=5,
    random_seed=42,
    verbose=False # ✅ force consistent results

)

model.fit(X_train, y_train)


# In[103]:


# 1) grab all df1 columns that start with "Ground_"
ground_cols = [c for c in df_with_ground.columns if c.startswith("Ground_")]

# 2) build a DataFrame of zeros with the same index as final_df
zeros_df = pd.DataFrame(
    0,
    index=final_df.index,
    columns=ground_cols
)

# 3) concatenate in one go
final_df_common = pd.concat([final_df_common, zeros_df], axis=1)


# In[104]:


final_df_common[f"Ground_{match_ground_for_model}"] = 1


# In[105]:


final_df_common.dropna(inplace=True)


# In[106]:


preds = model.predict(final_df_common)

# build res_df_fan with the same index as final_df
res_df_fan_all = pd.DataFrame(
    preds,
    index=final_df_common.index,
    columns=['PredictedFantasyPoints']
)

name_map = id_of_match.set_index('PlayerID')['Player Name']

# if res_df_fan doesn’t already have PlayerID, grab it from final_df
# res_df_fan_all['PlayerID'] = final_df_common['PlayerID']

# map names
res_df_fan_all['Player Name'] = res_df_fan_all.index.map(name_map)

# reorder columns if you like
res_df_fan_all = res_df_fan_all[['Player Name', 'PredictedFantasyPoints']]


# In[107]:


toss_win_team_inis2 = team_code_map.get(match_info['data']['tossWinner'])
toss_choice_of_win_team_ini = match_info['data']['tossChoice']
winner1 = ""
df_match_players = pd.read_excel("data/SquadPlayerNames_IndianT20League.xlsx",sheet_name= f"Match_{match_id_for_prediction}")
teams = list(df_match_players['Team'].unique())
if len(teams) != 2:
    raise ValueError(f"Expected exactly 2 unique teams, got {teams}")

# 2) figure out which key is the winner
if toss_win_team_inis2 in teams:
    winner1 = toss_win_team_inis2
else:
    # fallback: match first character
    init_char = toss_win_team_inis2[0].lower()
    matches = [t for t in teams if t and t[0].lower() == init_char]
    if len(matches) == 1:
        winner1 = matches[0]
    else:
        raise ValueError(
            f"Could not resolve winner from initials '{toss_win_team_inis2}' "
            f"against teams {teams}"
        )

def check_play_last(name: str, ptype: str) -> bool:
    # 1. Check mapping file exists
    if not os.path.isfile("Final_id_data_all.csv"):
        return False

    # 2. Load the CSV
    id_df = pd.read_csv("Final_id_data_all.csv")
    
    # 3. Check required columns
    if "Player Name" not in id_df.columns or "PlayerID" not in id_df.columns:
        return False

    # 4. Check if player name exists
    if name not in id_df["Player Name"].values:
        return False

    # 5. Get PlayerID
    pid_row = id_df[id_df["Player Name"] == name]
    if pid_row.empty:
        return False

    pid = str(pid_row["PlayerID"].values[0])
    folder = os.path.join("Data_players", pid)

    # 6. Check folder exists
    if not os.path.isdir(folder):
        return False

    # Helper to extract last fantasy points from a file
    def last_fp_from(file_name: str) -> float:
        path = os.path.join(folder, file_name)
        if not os.path.isfile(path):
            return 0.0

        df = pd.read_csv(path)
        if df.empty:
            return 0.0

        if "FantasyPoints" not in df.columns:
            return 0.0

        if df.shape[0] < 1:
            return 0.0

        last_val = df["FantasyPoints"].iloc[-1]
        if pd.isna(last_val):
            return 0.0

        try:
            val = float(last_val)
        except:
            return 0.0

        return val

    p = ptype.upper()
    
    if p in ("BAT", "WK"):
        return last_fp_from(f"{pid}_bat.csv") > 0

    elif p == "BOWL":
        return last_fp_from(f"{pid}_bowl.csv") > 0

    elif p == "ALL":
        bat_val = last_fp_from(f"{pid}_bat.csv")
        bowl_val = last_fp_from(f"{pid}_bowl.csv")
        return bat_val > 0 or bowl_val > 0

    return False
# In[108]:


class Player:
    def __init__(self, name: str, weight: float, profit: float, type_: str, team: int):
        self.name = name
        self.weight = weight
        self.profit = profit
        self.type = type_
        self.team = team

def prepare_players(
    df_match_players: pd.DataFrame,
    res_df_fan: pd.DataFrame,
    res_df_fan_bowl: pd.DataFrame,
    res_df_fan_all: pd.DataFrame,
    toss_win_team_ini: str,
    toss_choice_of_win_team_ini: str
) -> List[Player]:
    # 1) keep everyone except NOT_PLAYING
    playing = df_match_players[df_match_players["IsPlaying"] != "NOT_PLAYING"].copy()

    # 2) map team initials → ints
    unique_teams = playing["Team"].unique()
    team_map = {t: i+1 for i, t in enumerate(unique_teams)}
    # identify losing team (assume exactly 2 teams in the match)
    losing_team_ini = next(t for t in unique_teams if t != toss_win_team_ini)

    toss_choice = toss_choice_of_win_team_ini.lower()  # "bat" or "bowl"

    players: List[Player] = []

    # we'll track subs by team initial → list of (name, profit)
    subs_by_team = {t: [] for t in unique_teams}
    
    for _, row in playing.iterrows():
        name     = row["Player Name"]
        weight   = float(row["Credits"])
        ptype    = row["Player Type"].upper()   # "BAT","BOWL","ALL","WK"
        team_ini = row["Team"]
        team     = team_map[team_ini]

        # detect substitute by IsPlaying flag
        is_sub = (row["IsPlaying"] == "X_FACTOR_SUBSTITUTE")

        # if a substitute, only keep them if they played in the last match
        if is_sub:
            played_last = check_play_last(name, ptype)
            if not played_last:
                continue
        #hh
        # lookup all three fantasy scores up front
        c_bat  = float(
            res_df_fan.loc[
                res_df_fan["Player Name"] == name, "PredictedFantasyPoints"
            ].squeeze()
        ) if name in res_df_fan["Player Name"].values else 0.0

        c_bowl = float(
            res_df_fan_bowl.loc[
                res_df_fan_bowl["Player Name"] == name, "PredictedFantasyPoints"
            ].squeeze()
        ) if name in res_df_fan_bowl["Player Name"].values else 0.0

        c_all  = float(
            res_df_fan_all.loc[
                res_df_fan_all["Player Name"] == name, "PredictedFantasyPoints"
            ].squeeze()
        ) if name in res_df_fan_all["Player Name"].values else 0.0

        #hh1
        #hh
        # determine kind and base profit
        if ptype in ("BAT", "WK"):
            profit = c_bat
            kind   = "BATSMAN" if ptype == "BAT" else "WICKETKEEPER"

        elif ptype == "BOWL":
            profit = c_bowl
            kind   = "BOWLER"

        elif ptype == "ALL":
            kind = "ALLROUNDER"
            if is_sub:
                # ALL-rounder sub: only second-innings contribution
                if team_ini == toss_win_team_ini:
                    # toss-winner
                    if toss_choice == "bat":
                        # winner bats 1st → bowls 2nd
                        profit = c_bowl
                    else:
                        # winner bowls 1st → bats 2nd
                        profit = c_bat
                else:
                    # losing side
                    if toss_choice == "bat":
                        # losing bowls 1st → bats 2nd
                        profit = c_bat
                    else:
                        # losing bats 1st → bowls 2nd
                        profit = c_bowl
            else:
                # non-subs still get their full ALL score
                profit = max(c_all, c_bowl, c_bat)

        else:
            # unknown type → skip
            continue

            

        #hh1
        # now also zero-out any unwanted subs for pure BAT/BOWL/WK as before:
        if is_sub and ptype != "ALL":
            if team_ini == toss_win_team_ini:
                if toss_choice == "bat" and kind in ("BATSMAN", "WICKETKEEPER"):
                    profit = 0.0
                if toss_choice == "bowl" and kind == "BOWLER":
                    profit = 0.0
            elif team_ini == losing_team_ini:
                if toss_choice == "bat" and kind == "BOWLER":
                    profit = 0.0
                if toss_choice == "bowl" and kind in ("BATSMAN", "WICKETKEEPER"):
                    profit = 0.0

        players.append(Player(name, weight, profit, kind, team))
        # if substitute, track it for possible later removal
        if is_sub:
            subs_by_team[team_ini].append((name, profit))
        # apply toss/sub logic: zero out unwanted subs
    # --- Now prune substitutes: keep only highest-profit sub per team ---
    to_remove = set()
    for team_ini, subs in subs_by_team.items():
        # if more than one sub, drop all but the top-profit
        if len(subs) > 1:
            # find the name of the sub with max profit
            best_name, _ = max(subs, key=lambda x: x[1])
            # mark all other subs for removal
            for name, _ in subs:
                if name != best_name:
                    to_remove.add(name)

    # filter out those marked names
    players = [p for p in players if p.name not in to_remove]
    
    return players

def solve(
    players: List[Player],
    max_weight: float = 100,
    max_players: int = 11,
    type_limits: dict = {
        "BATSMAN": (1, 8),
        "BOWLER": (1, 4),
        "WICKETKEEPER": (1, 8),
        "ALLROUNDER": (1, 4),
    }
):
    dp = defaultdict(dict)
    init_state = (0, 0, 0, 0, 0, 0, 0, 0)  # weight, bat, bowl, wk, all, t1, t2, count
    dp[0][init_state] = (0, [])

    for pl in players:
        new_dp = defaultdict(dict)
        # carry over old states
        for w, states in dp.items():
            for st, val in states.items():
                new_dp[w][st] = val

        # try adding this player
        for w, states in dp.items():
            for st, (prof, team_list) in states.items():
                cw, bat, bowl, wk, ar, t1, t2, cnt = st

                nw = cw + pl.weight
                if nw > max_weight:
                    continue

                nbat  = bat  + (pl.type == "BATSMAN")
                nbowl = bowl + (pl.type == "BOWLER")
                nwk   = wk   + (pl.type == "WICKETKEEPER")
                nar   = ar   + (pl.type == "ALLROUNDER")
                # type caps
                if (
                    nbat  > type_limits["BATSMAN"][1]     or
                    nbowl > type_limits["BOWLER"][1]      or
                    nwk   > type_limits["WICKETKEEPER"][1] or
                    nar   > type_limits["ALLROUNDER"][1]
                ):
                    continue

                nt1 = t1 or (pl.team == 1)
                nt2 = t2 or (pl.team == 2)
                ncnt = cnt + 1
                if ncnt > max_players:
                    continue

                new_st = (nw, nbat, nbowl, nwk, nar, nt1, nt2, ncnt)
                nprof  = prof + pl.profit
                nteam  = team_list + [pl.name]

                if new_st not in new_dp[nw] or nprof > new_dp[nw][new_st][0]:
                    new_dp[nw][new_st] = (nprof, nteam)

        dp = new_dp

    # pick best valid team
    best_profit = 0
    best_team   = []
    for states in dp.values():
        for st, (prof, team_list) in states.items():
            _, bat, bowl, wk, ar, t1, t2, cnt = st
            if (
                cnt == max_players and
                bat >= 1 and bowl >= 1 and wk >= 1 and ar >= 1 and
                t1 and t2
            ) and prof > best_profit:
                best_profit = prof
                best_team   = team_list

    # sort the 11 by predicted points descending
    profit_map = {pl.name: pl.profit for pl in players}
    sorted_team = sorted(best_team, key=lambda n: profit_map[n], reverse=True)
    # 1) Build a map from player name → team initial
    team_map = df_match_players.set_index("Player Name")["Team"].to_dict()

    # 2) Identify C and VC
    captain = sorted_team[0]
    vice    = sorted_team[1]

    # 3) Assemble rows
    rows = []
    for idx, name in enumerate(sorted_team):
        flag = ""
        if idx == 0:
            flag = "C"
        elif idx == 1:
            flag = "VC"
        rows.append({
            "Player name": name,
            "Team":        team_map.get(name, ""),
            "C/VC":        flag
        })

    # 4) Make DataFrame & save
    out_df = pd.DataFrame(rows)

    fname = "data/Ignitors_output.csv"
    out_df.to_csv(fname, index=False)

# Replace these with actual DataFrames
df_match_players = pd.read_excel("data/SquadPlayerNames_IndianT20League.xlsx",sheet_name= f"Match_{match_id_for_prediction}")
# res_df_fan = pd.read_csv("fan_bat.csv")
# res_df_fan_bowl = pd.read_csv("fan_bowl.csv")
# res_df_fan_all = pd.read_csv("fan_all.csv")

players = prepare_players(
    df_match_players,
    res_df_fan,
    res_df_fan_bowl,
    res_df_fan_all,
    winner1,
    toss_choice_of_win_team_ini
)
solve(players)


# In[ ]:


print(f"Ignitors_output.csv saved in Downloads folder")




# In[ ]:





# In[ ]:






# In[ ]:



