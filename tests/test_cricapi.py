from fantasy_predictor.cricapi import PLAYOFF_MATCH_IDS, find_match_id_by_number, find_match_id_by_title

MATCHES = [
    {"id": "a", "name": "Kolkata Knight Riders vs Royal Challengers Bengaluru, 1st Match", "date": "2025-03-22"},
    {"id": "b", "name": "Sunrisers Hyderabad vs Rajasthan Royals, 2nd Match", "date": "2025-03-23"},
    {"id": "q", "name": "Punjab Kings vs Royal Challengers Bengaluru, Qualifier 1", "date": "2025-05-29"},
]


def test_find_by_title_and_date():
    assert find_match_id_by_title(MATCHES, "23-03-2025", "Sunrisers Hyderabad vs Rajasthan Royals") == "b"


def test_find_by_title_needs_the_same_date():
    assert find_match_id_by_title(MATCHES, "24-03-2025", "Sunrisers Hyderabad vs Rajasthan Royals") is None


def test_find_by_number_reads_the_digits_in_the_name():
    assert find_match_id_by_number(MATCHES, "2") == "b"
    # "Qualifier 1" contains the digit 1, but must not be mistaken for match 1
    assert find_match_id_by_number(MATCHES, "1") == "a"


def test_playoffs_use_fixed_ids():
    assert find_match_id_by_number(MATCHES, "71") == PLAYOFF_MATCH_IDS[71]
