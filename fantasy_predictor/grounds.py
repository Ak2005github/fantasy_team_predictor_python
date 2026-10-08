"""Stage 1e: build the ground lookup table used to match a fixture's venue to Statsguru grounds."""
import os

import pandas as pd
from bs4 import BeautifulSoup

from .config import GROUND_TABLE_CSV, PLAYERS_DIR
from .net import BROWSER_HEADERS, get_with_retry


def get_ground_label(url_id):
    """Return the Statsguru page title for a ground, or "Unknown"."""
    url = f"https://stats.espncricinfo.com/ci/engine/ground/{url_id}.html?class=6;type=aggregate"
    response = get_with_retry(url, headers=BROWSER_HEADERS, timeout=10, retry_on=(Exception,), delay=0)
    soup = BeautifulSoup(response.text, "html.parser")
    link_tag = soup.find("a", href="/records")
    if link_tag:
        return link_tag.text.strip()
    else:
        return "Unknown"


def build_ground_table(players_dir=PLAYERS_DIR, out_csv=GROUND_TABLE_CSV):
    """Count appearances per ground since 2023 and attach each ground's full name."""
    root_folder = players_dir

    # Ground value counts per file
    ground_counts = {}

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

    # Map each Ground Link to the short ground name used in the innings tables
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

                except Exception:
                    pass
    combined_ground_counts["corr_ground"] = combined_ground_counts.index.map(ground_link_to_name)

    sorted_ground_counts = combined_ground_counts.sort_values(by='Total', ascending=False)

    # Extract the number at the end of each URL in the index
    sorted_ground_counts["id_gr"] = sorted_ground_counts.index.str.extract(r'(\d+)\.html$')[0].astype(int).values

    sorted_ground_counts["Name_gr_ex"] = [get_ground_label(url) for url in sorted_ground_counts['id_gr']]

    # Keep only the ground's full name from the page title
    sorted_ground_counts["Name_gr_ex"] = sorted_ground_counts["Name_gr_ex"].str.extract(
        r'Statsguru / (.+?) / Twenty20 matches'
    )

    sorted_ground_counts.to_csv(out_csv)
    return sorted_ground_counts


def load_ground_table(path=GROUND_TABLE_CSV):
    df_gr_data = pd.read_csv(path)
    return df_gr_data[["Ground Link", "corr_ground", "id_gr", "Name_gr_ex"]]


def find_ground_info(df_gr_data, full_name: str):
    """
    Given a full ground name, return (corr_ground, Ground Link) from df_gr_data.
    1) Try exact match (case-insensitive) on Name_gr_ex.
    2) If none, take prefix before first comma and look for that substring.
    """
    # lowercase everything for case-insensitive comparison
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
