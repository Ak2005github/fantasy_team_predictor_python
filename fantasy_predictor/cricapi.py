"""CricAPI lookups: the season's match list, a match's ID, and its toss and venue."""
import time
from datetime import datetime

import pandas as pd
import requests

from .config import MATCHES_CORRECTED_CSV

SERIES_INFO_URL = 'https://api.cricapi.com/v1/series_info?'
MATCH_INFO_URL = 'https://api.cricapi.com/v1/match_info?'

# CricAPI IDs of the playoff fixtures, whose names carry no match number
PLAYOFF_MATCH_IDS = {
    71: "1c2f9a38-4c3a-407b-90c1-9b78dee63cb8",
    72: "40596379-a096-4513-8b6f-41df069ca70c",
    73: "08b32e61-9c96-4f37-8f76-0b3439a80567",
    74: "b70371b1-6528-4af6-992c-e880ed585183",
}


def get_series_info(apikey, series_id):
    url = f"{SERIES_INFO_URL}apikey={apikey}&id={series_id}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to retrieve data: {response.status_code}")


def get_match_info(apikey, match_id):
    url = f"{MATCH_INFO_URL}apikey={apikey}&id={match_id}"
    response = requests.get(url)
    if(response.status_code == 200):
        return response.json()
    else:
        return f'Failed to retrieve data{response}'


def find_match_id_by_title(ipl_matches_list, date, x_vs_y):
    """CricAPI ID of the match called ``x_vs_y`` on ``date`` (dd-mm-yyyy), or None."""
    date = datetime.strptime(date, "%d-%m-%Y")

    for match in ipl_matches_list:
        name = match['name'].split(",")[0]
        match_date = datetime.strptime(match['date'], "%Y-%m-%d")
        if x_vs_y == name and date == match_date:
            return match["id"]

    return None


def find_match_id_by_number(ipl_matches_list, number):
    """CricAPI ID of league match ``number`` (the digits in its name); playoffs use fixed IDs."""
    if int(number) in PLAYOFF_MATCH_IDS:
        return PLAYOFF_MATCH_IDS[int(number)]

    for match in ipl_matches_list:
        match_name = match['name']
        num = ""

        for ch in match_name:
            if(ch.isnumeric()):
                num += ch
        if(number == num and  'Qualifier' not in match_name):
            match_id = match['id']

    return match_id


def _default_toss(match_info):
    """Without toss data, assume the first-named team bats first."""
    if 'tossWinner' not in match_info['data']:
        first_team = match_info['data']['name'].split(" vs ")[0]
        match_info['data']['tossWinner']=first_team
        match_info['data']['tossChoice']='bat'


def match_info_from_schedule(apikey, ipl_matches_list, match_number, corrected_csv=MATCHES_CORRECTED_CSV):
    """Step 1 lookup: find the match by title and date, retrying once if the toss is not out yet.

    Falls back to the fixture list (venue, date, first-named team batting) when
    CricAPI does not list the match. Returns (match_info, cut_date).
    """
    df_mat = pd.read_csv(corrected_csv)
    row = df_mat.loc[df_mat['Match Number'] == int(match_number)].iloc[0]

    mat_name = row['Match Title'].split(',', 1)[0]
    mat_venue = row['Venue']
    mat_date = row['Date']

    ipl_match_id = find_match_id_by_title(ipl_matches_list, mat_date, mat_name)

    if ipl_match_id is not None:
        nn=2
        while nn:
            match_info = get_match_info(apikey, ipl_match_id)
            nn-=1
            if 'tossWinner' in match_info['data']:
                break
            else:
                time.sleep(21)

        _default_toss(match_info)
    else:
        first_team = mat_name.split(" vs ")[0]
        match_info = { 'data': {} }
        match_info['data']['tossWinner']=first_team
        match_info['data']['tossChoice']='bat'
        match_info['data']['venue']=mat_venue
        match_info['data']['date']=mat_date
        dt12 = datetime.strptime(match_info['data']['date'], '%d-%m-%Y')
        match_info['data']['date'] = dt12.strftime('%Y-%m-%d')

    cut_date = pd.to_datetime(match_info['data']['date'])
    return match_info, cut_date


def match_info_by_number(apikey, ipl_matches_list, match_number):
    """Step 2 lookup, after the toss: fetch the match by number. Returns (match_info, cut_date)."""
    number = str(match_number)
    ipl_match_id = find_match_id_by_number(ipl_matches_list, number)

    match_info = get_match_info(apikey, ipl_match_id)
    if 'tossWinner' not in match_info['data']:
        print("Try after 5 mins")
    _default_toss(match_info)

    cut_date = pd.to_datetime(match_info['data']['date'])
    return match_info, cut_date
