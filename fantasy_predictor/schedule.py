"""Season fixtures (Cricbuzz) and the team-code table (Wikipedia)."""
import csv
from datetime import datetime, timezone

import pandas as pd
import requests
from bs4 import BeautifulSoup

from .config import (CRICBUZZ_FIXTURES_URL, MATCH_DATES_CSV, MATCHES_CORRECTED_CSV, MATCHES_CSV,
                     POINTS_TABLE_CSV, WIKIPEDIA_SEASON_URL)
from .net import BROWSER_HEADERS, get_with_retry

PLAYOFF_NUMBERS = {
    'Qualifier 1': 71,
    'Eliminator':   72,
    'Qualifier 2': 73,
    'Final':       74
}


def scrape_fixtures(url=CRICBUZZ_FIXTURES_URL, out_csv=MATCHES_CSV):
    """Save every fixture's title, venue, result and UTC start time."""
    response = get_with_retry(url, headers=BROWSER_HEADERS, timeout=40, retry_on=(Exception,),
                              max_attempts=15)
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

    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Match Title", "Venue", "Result", "Date (UTC)", "Raw Time (GMT/Local)"])
        writer.writerows(data)


def build_fixture_tables(matches_csv=MATCHES_CSV, corrected_csv=MATCHES_CORRECTED_CSV, dates_csv=MATCH_DATES_CSV):
    """Number every fixture (playoffs are 71-74) and save the match-number to date table."""
    df = pd.read_csv(matches_csv)

    # Extract the digits immediately followed by "st/nd/rd/th Match"
    df['Match Number'] = df['Match Title']\
        .str.extract(r'(\d+)(?=st Match|nd Match|rd Match|th Match)', expand=False)

    # Assign special playoff numbers
    for keyword, num in PLAYOFF_NUMBERS.items():
        mask = df['Match Title'].str.contains(keyword)
        df.loc[mask, 'Match Number'] = num

    # Drop rows where that pattern wasn't found
    df = df.dropna(subset=['Match Number'])

    df['Match Number'] = df['Match Number'].astype(int)
    df = df.sort_values('Match Number').reset_index(drop=True)

    df['Date'] = (
        pd.to_datetime(df['Date (UTC)'].str.split().str[0], format='%Y-%m-%d')
          .dt.strftime('%d-%m-%Y')
    )

    df.to_csv(corrected_csv, index=False)
    df[['Match Number','Date']].to_csv(dates_csv,index=False)


def scrape_points_table(url=WIKIPEDIA_SEASON_URL, out_csv=POINTS_TABLE_CSV):
    """Save the season summary table, whose header row maps team names to codes."""
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    table = soup.find('table', class_='wikitable module-CricketLeagueGroupStageSummary')

    if table is None:
        raise Exception("Points table not found. Check the class name or table structure.")

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

    df = pd.DataFrame(data, columns=headers)
    df.to_csv(out_csv, index=False)


def load_team_codes(points_csv=POINTS_TABLE_CSV):
    """Map each full team name (e.g. 'Chennai Super Kings') to its code (e.g. 'CSK')."""
    df_ini_teams = pd.read_csv(points_csv, index_col=0)
    return dict(zip(df_ini_teams.index, df_ini_teams.columns))
