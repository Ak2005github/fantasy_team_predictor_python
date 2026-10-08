import itertools
import random

import pandas as pd
import pytest

from fantasy_predictor.optimizer import DEFAULT_TYPE_LIMITS, Player, prepare_players, select_team, solve

ROLES = ["BATSMAN", "BOWLER", "WICKETKEEPER", "ALLROUNDER"]


def is_valid(team, max_weight=100, size=11, limits=DEFAULT_TYPE_LIMITS):
    if len(team) != size or sum(p.weight for p in team) > max_weight:
        return False
    for role, (lo, hi) in limits.items():
        n = sum(p.type == role for p in team)
        if not lo <= n <= hi:
            return False
    return {p.team for p in team} == {1, 2}


def brute_force_best(players):
    best = None
    for combo in itertools.combinations(players, 11):
        if is_valid(combo):
            total = sum(p.profit for p in combo)
            if best is None or total > best:
                best = total
    return best


def random_squad(rng, n):
    players = []
    for i in range(n):
        role = ROLES[i % 4] if i < 4 else rng.choice(ROLES)
        players.append(Player(f"P{i}", rng.choice([6.5, 7, 7.5, 8, 8.5, 9, 9.5, 10]),
                              round(rng.uniform(5, 80), 1), role, 1 + (i % 2)))
    return players


@pytest.mark.parametrize("seed", range(30))
def test_dp_matches_brute_force(seed):
    rng = random.Random(seed)
    players = random_squad(rng, 15)

    profit, names = select_team(players)
    expected = brute_force_best(players)

    if expected is None:
        assert names == []
    else:
        chosen = [p for p in players if p.name in names]
        assert is_valid(chosen)
        assert profit == pytest.approx(expected)
        assert sum(p.profit for p in chosen) == pytest.approx(expected)


def test_budget_forces_cheaper_players():
    # 11 cheap players and one expensive star; the star fits only if the rest stay cheap
    players = [Player(f"Cheap{i}", 8, 10, ROLES[i % 4], 1 + i % 2) for i in range(11)]
    players.append(Player("Star", 30, 100, "BATSMAN", 1))
    profit, names = select_team(players)
    assert "Star" not in names  # 30 + 10 x 8 = 110 credits is over budget
    assert profit == pytest.approx(110)


def test_solve_writes_captain_and_vice_captain(tmp_path):
    rng = random.Random(3)
    players = random_squad(rng, 15)
    squad = pd.DataFrame({"Player Name": [p.name for p in players],
                          "Team": ["AAA" if p.team == 1 else "BBB" for p in players]})
    out = tmp_path / "team.csv"

    team = solve(players, squad, out)

    saved = pd.read_csv(out, keep_default_na=False)
    assert list(saved.columns) == ["Player name", "Team", "C/VC"]
    assert len(saved) == 11
    assert list(saved["C/VC"][:2]) == ["C", "VC"] and set(saved["C/VC"][2:]) == {""}
    by_name = {p.name: p.profit for p in players}
    captain_points = by_name[team["Player name"].iloc[0]]
    assert captain_points == max(by_name[n] for n in team["Player name"])


def test_substitutes_count_only_for_the_innings_they_can_play(tmp_path, monkeypatch):
    # The toss winner bats first, so its impact-player batter would come in too late to bat
    monkeypatch.chdir(tmp_path)
    pd.DataFrame({"Player Name": ["Sub Bat", "Sub Bowl"], "PlayerID": [1, 2]}).to_csv("Final_id_data_all.csv")
    for pid, kind in [(1, "bat"), (2, "bowl")]:
        (tmp_path / "Data_players" / str(pid)).mkdir(parents=True)
        pd.DataFrame({"FantasyPoints": [12.0]}).to_csv(tmp_path / "Data_players" / str(pid) / f"{pid}_{kind}.csv")

    squad = pd.DataFrame({
        "Player Name": ["Sub Bat", "Sub Bowl", "Regular"],
        "Credits": [7, 7, 8],
        "Player Type": ["BAT", "BOWL", "BAT"],
        "Team": ["AAA", "AAA", "BBB"],
        "IsPlaying": ["X_FACTOR_SUBSTITUTE", "X_FACTOR_SUBSTITUTE", "PLAYING"],
    })
    preds = pd.DataFrame({"Player Name": ["Sub Bat", "Sub Bowl", "Regular"],
                          "PredictedFantasyPoints": [40.0, 35.0, 30.0]})

    players = prepare_players(squad, preds, preds, preds, "AAA", "bat")

    names = [p.name for p in players]
    # only the better of a team's two substitutes is kept, after the toss adjustment
    assert names == ["Sub Bowl", "Regular"]
    assert players[0].profit == 35.0
