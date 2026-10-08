"""Stage 1c: download each player's innings-by-innings T20 records from Statsguru."""
import os

import pandas as pd
import requests
from bs4 import BeautifulSoup

from .config import PLAYERS_DIR
from .net import BROWSER_HEADERS, get_with_retry

STATSGURU_VIEWS = {
    "bat": "type=batting;view=innings",
    "bowl": "type=bowling;view=innings",
    "bowl_wic": "type=bowling;view=dismissal_list",
    "field": "type=fielding;view=innings"
}

# 1-based position of the Ground column in each view (None: view has no links)
GROUND_COLUMN = {
    "bat": 12,
    "bowl": 10,
    "bowl_wic": None,
    "field": 9
}

# Which Statsguru views to download for each player role
VIEWS_BY_ROLE = {
    "BAT": ["bat", "field"],
    "BOWL": ["bowl", "bowl_wic", "field"],
    "WK": ["bat", "field"],
    "ALL": ["bat", "bowl", "bowl_wic", "field"]
}


def scrape_data(player_id, data_type, players_dir=PLAYERS_DIR):
    """Save one Statsguru innings table for a player as ``<dir>/<id>/<id>_<type>.csv``."""
    base_url = f"https://stats.espncricinfo.com/ci/engine/player/{player_id}.html?class=6;template=results;"

    i = GROUND_COLUMN[data_type]
    if data_type not in STATSGURU_VIEWS:
        raise ValueError(f"Invalid data_type: {data_type}. Must be one of {list(STATSGURU_VIEWS.keys())}")

    url = base_url + STATSGURU_VIEWS[data_type]
    response = get_with_retry(url, headers=BROWSER_HEADERS, timeout=40,
                              retry_on=(requests.exceptions.RequestException,))
    soup = BeautifulSoup(response.text, 'html.parser')

    # Locate all tables with class 'engineTable'
    tables = soup.find_all('table', class_='engineTable')

    # Check if there are enough tables
    if len(tables) < 3:
        return

    # The innings list is the 4th results table on the page
    table = tables[3]

    # Extract table headers
    headers = [th.text.strip() for th in table.find_all('th')]
    headers.append("Ground Link")
    headers.append("Team Link")

    if 'BPO' in headers:
        i += 1

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
    save_dir = f"{players_dir}/{player_id}"
    os.makedirs(save_dir, exist_ok=True)  # Ensure the player_id directory exists

    save_path = f"{save_dir}/{player_id}_{data_type}.csv"
    df.to_csv(save_path, index=False)
    return df


def scrape_players(df, players_dir=PLAYERS_DIR):
    """Download every Statsguru view relevant to each player's role."""
    os.makedirs(players_dir, exist_ok=True)
    for _, row in df.iterrows():
        player_id = row["PlayerID"]
        player_type = row["Player Type"]

        if player_type in VIEWS_BY_ROLE:
            for query in VIEWS_BY_ROLE[player_type]:
                scrape_data(player_id, query, players_dir)
