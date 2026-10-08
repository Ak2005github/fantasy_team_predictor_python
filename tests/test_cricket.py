import pytest

from fantasy_predictor.cricket import convert_overs_to_balls, innings_map, resolve_toss_winner


@pytest.mark.parametrize("overs,balls", [("4", 24), ("3.4", 22), (2.0, 12), ("0.5", 5), ("-", None), ("DNB", None)])
def test_convert_overs_to_balls(overs, balls):
    assert convert_overs_to_balls(overs) == balls


def test_toss_winner_falls_back_to_first_letter():
    # the points table says CSK while the squad sheet says CHE
    assert resolve_toss_winner(["CHE", "MI"], "CSK") == "CHE"
    assert resolve_toss_winner(["CHE", "MI"], "MI") == "MI"


def test_toss_winner_must_be_unambiguous():
    with pytest.raises(ValueError):
        resolve_toss_winner(["KKR", "KXI"], "KAP")
    with pytest.raises(ValueError):
        resolve_toss_winner(["CHE", "MI", "RCB"], "MI")


@pytest.mark.parametrize("choice,bowling,expected", [
    ("bat", False, {"CHE": 1, "MI": 2}),   # winner bats first
    ("bowl", False, {"CHE": 2, "MI": 1}),
    ("bat", True, {"CHE": 2, "MI": 1}),    # ...so it bowls second
    ("bowl", True, {"CHE": 1, "MI": 2}),
])
def test_innings_map(choice, bowling, expected):
    assert innings_map(["CHE", "MI"], "CHE", choice, bowling=bowling) == expected


def test_innings_map_rejects_unknown_choice():
    with pytest.raises(ValueError):
        innings_map(["CHE", "MI"], "CHE", "field")
