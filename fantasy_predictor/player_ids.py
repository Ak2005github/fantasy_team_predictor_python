"""Stage 1b: resolve every squad player to an ESPNcricinfo player ID."""
import pandas as pd
from bs4 import BeautifulSoup

from .net import get_with_retry

SEARCH_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/115.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,/;q=0.8"
}

# Players whose name search returns several (or no) ESPNcricinfo profiles,
# mapped by hand to the right ID.
DISCREPANCY_PLAYERS = {
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


def extract_player_id_from_tag(tag_html):
    """Pull the numeric player ID out of a Statsguru player link."""
    if tag_html:
        soup = BeautifulSoup(tag_html, 'html.parser')
        a_tag = soup.find('a', class_='statsLinks', href=True)
        if a_tag:
            href = a_tag['href']
            player_id = href.split('/player/')[-1].split('.html')[0]
            return player_id
    return None


def fetch_player_tags(player_name):
    """Search Statsguru for a player name and return the T20 profile IDs it lists."""
    url = f"https://stats.espncricinfo.com/ci/engine/stats/analysis.html?search={'+'.join(player_name.split())};template=analysis"
    response = get_with_retry(url, headers=SEARCH_HEADERS, timeout=40, retry_on=(Exception,))

    if response.status_code != 200:
        return None

    soup = BeautifulSoup(response.text, 'html.parser')
    player_div = soup.find('div', id='gurusearch_player')
    if not player_div:
        return None

    a_tags = player_div.find_all('a', class_='statsLinks', href=lambda h: h and 'class=6' in h)
    return [extract_player_id_from_tag(str(a_tag)) for a_tag in a_tags]


def add_player_ids(df, discrepancy_players=DISCREPANCY_PLAYERS):
    """Add a PlayerID column, using the manual map when the search is ambiguous."""
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


def build_player_id_file(workbook_path, out_csv):
    """Resolve IDs for the master squad sheet, save them, and return the saved table."""
    df = pd.read_excel(workbook_path, sheet_name='SquadData_AllTeams')
    df = add_player_ids(df)
    df.to_csv(out_csv)
    return pd.read_csv(out_csv, index_col=0)

