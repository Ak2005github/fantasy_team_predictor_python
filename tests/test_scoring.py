import numpy as np
import pandas as pd
import pytest

from fantasy_predictor.scoring import (batting_points, bowling_points, out_value, process_fantasy_points_bat,
                                       process_fantasy_points_field)


def bat(runs, bf, fours=0, sixes=0, out=1):
    sr = runs / bf * 100 if bf else 0
    return {"Runs": runs, "BF": bf, "SR": sr, "4s": fours, "6s": sixes, "out": out}


def test_half_century_with_boundaries_and_fast_strike_rate():
    # 52 runs + 5x4 + 2x6 boundary bonus + 8 (50+) + 6 (SR > 170)
    assert batting_points(bat(52, 30, fours=5, sixes=2)) == 52 + 20 + 12 + 8 + 6


@pytest.mark.parametrize("runs,bonus", [(25, 4), (49, 4), (50, 8), (75, 12), (100, 16), (24, 0)])
def test_only_the_highest_run_milestone_counts(runs, bonus):
    # 10 balls or fewer: no strike-rate adjustment
    assert batting_points(bat(runs, 10)) == runs + bonus


def test_duck_costs_two_points_only_when_dismissed():
    assert batting_points(bat(0, 3, out=1)) == -2
    assert batting_points(bat(0, 3, out=0)) == 0


@pytest.mark.parametrize("runs,bf,adjust", [
    (10, 20, -4),   # SR 50
    (12, 20, -2),   # SR 60
    (14, 20, 0),    # SR 70
    (26, 20, 2 + 4),  # SR 130, plus the 25-run bonus
    (11, 11, 0),    # SR 100
])
def test_strike_rate_adjustment_after_ten_balls(runs, bf, adjust):
    assert batting_points(bat(runs, bf)) == runs + adjust


def test_out_value_flags():
    assert out_value("45") == 1
    assert out_value("45*") == 0
    assert np.isnan(out_value("DNB"))


def test_bowling_points_count_only_bowler_wickets():
    row = {"Overs": 4.0, "Mdns": 0, "Runs": 24, "Econ": 6.0}
    wickets = pd.DataFrame({"How out": ["caught", "bowled", "lbw", "run out"]})
    # 3 wickets x 30, 2 bowled/lbw x 8, 3-wicket bonus 4, economy 6.0 -> +2,
    # estimated dots: 24 balls - (24/5 + 24/3) = 11.2 -> 11
    assert bowling_points(row, wickets) == 90 + 16 + 4 + 2 + 11


def test_expensive_spell_is_penalised():
    row = {"Overs": 2.0, "Mdns": 0, "Runs": 30, "Econ": 15.0}
    no_wickets = pd.DataFrame({"How out": pd.Series([], dtype=str)})
    # economy 15 -> -6; estimated dots 12 - (6 + 10) < 0 -> 0
    assert bowling_points(row, no_wickets) == -6


def test_fielding_file_points(tmp_path):
    path = tmp_path / "1_field.csv"
    pd.DataFrame({
        "Dis": ["4", "TDNF"], "Ct": [3, 0], "St": [1, 0], "Ct Wk": [0, 0], "Ct Fi": [3, 0],
        "Inns": [1, 2], "Opposition": ["v A", "v B"], "Ground": ["X", "Y"], "Start Date": ["1 Apr 2024", "2 Apr 2024"],
    }).to_csv(path, index=False)

    process_fantasy_points_field(path)

    out = pd.read_csv(path)
    assert len(out) == 1  # the TDNF row is dropped
    # 3 catches x 8, 3-catch bonus 4, 1 stumping x 12
    assert out["FantasyPoints"].iloc[0] == 24 + 4 + 12


def test_batting_file_skips_tdnb_and_marks_dnb(tmp_path):
    path = tmp_path / "1_bat.csv"
    cols = ['Runs', 'Mins', 'BF', '4s', '6s', 'SR', 'Pos', 'Dismissal', 'Inns', 'Unnamed: 9',
            'Opposition', 'Ground', 'Start Date', 'Unnamed: 13']
    rows = [
        ["30*", 20, 20, 3, 1, 150.0, 3, "not out", 1, None, "v A", "X", "1 Apr 2024", None],
        ["DNB", "-", "-", "-", "-", "-", "-", "-", 2, None, "v B", "Y", "3 Apr 2024", None],
        ["TDNB", "-", "-", "-", "-", "-", "-", "-", 1, None, "v C", "Z", "5 Apr 2024", None],
    ]
    pd.DataFrame(rows, columns=cols).to_csv(path, index=False)

    process_fantasy_points_bat(path)

    out = pd.read_csv(path)
    assert list(out["Runs"].fillna(-1)) == [30, -1]
    assert out["out"].iloc[0] == 0 and pd.isna(out["out"].iloc[1])
    # 30 + 3x4 + 1x6 + 4 (25+) + 2 (SR 150)
    assert out["FantasyPoints"].iloc[0] == 30 + 12 + 6 + 4 + 2
