"""Stage 2c: choose the best valid XI with dynamic programming, then captain and vice-captain.

The selection is a knapsack with extra constraints: 11 players within the
100-credit budget, role minimums and maximums, and at least one player from
each team. The DP state is (credits used, count per role, team flags,
players picked), and for each state only the highest predicted total is kept.
"""
import os
from collections import defaultdict
from typing import List

import pandas as pd

from .config import OUTPUT_CSV, PLAYER_ID_CSV, PLAYERS_DIR

DEFAULT_TYPE_LIMITS = {
    "BATSMAN": (1, 8),
    "BOWLER": (1, 4),
    "WICKETKEEPER": (1, 8),
    "ALLROUNDER": (1, 4),
}


class Player:
    def __init__(self, name: str, weight: float, profit: float, type_: str, team: int):
        self.name = name
        self.weight = weight    # credits
        self.profit = profit    # predicted fantasy points
        self.type = type_
        self.team = team        # 1 or 2

    def __repr__(self):
        return f"Player({self.name!r}, {self.weight}, {self.profit:.1f}, {self.type}, team {self.team})"


def check_play_last(name: str, ptype: str, id_csv=PLAYER_ID_CSV, players_dir=PLAYERS_DIR) -> bool:
    """True if the player scored fantasy points in their most recent recorded innings."""
    # 1. Check mapping file exists
    if not os.path.isfile(id_csv):
        return False

    # 2. Load the CSV
    id_df = pd.read_csv(id_csv)

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
    folder = os.path.join(players_dir, pid)

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
        except Exception:
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


def _predicted(res_df, name):
    if name in res_df["Player Name"].values:
        return float(res_df.loc[res_df["Player Name"] == name, "PredictedFantasyPoints"].squeeze())
    return 0.0


def prepare_players(
    df_match_players: pd.DataFrame,
    res_df_fan: pd.DataFrame,
    res_df_fan_bowl: pd.DataFrame,
    res_df_fan_all: pd.DataFrame,
    toss_win_team_ini: str,
    toss_choice_of_win_team_ini: str
) -> List[Player]:
    """Turn the match squad and the three models' predictions into selectable players.

    Impact-player substitutes only count for the innings they can play, given the toss.
    """
    # 1) keep everyone except NOT_PLAYING
    playing = df_match_players[df_match_players["IsPlaying"] != "NOT_PLAYING"].copy()

    # 2) map team initials -> ints
    unique_teams = playing["Team"].unique()
    team_map = {t: i+1 for i, t in enumerate(unique_teams)}
    # identify losing team (assume exactly 2 teams in the match)
    losing_team_ini = next(t for t in unique_teams if t != toss_win_team_ini)

    toss_choice = toss_choice_of_win_team_ini.lower()  # "bat" or "bowl"

    players: List[Player] = []

    # we'll track subs by team initial -> list of (name, profit)
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

        # lookup all three fantasy scores up front
        c_bat  = _predicted(res_df_fan, name)
        c_bowl = _predicted(res_df_fan_bowl, name)
        c_all  = _predicted(res_df_fan_all, name)

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
                        # winner bats 1st -> bowls 2nd
                        profit = c_bowl
                    else:
                        # winner bowls 1st -> bats 2nd
                        profit = c_bat
                else:
                    # losing side
                    if toss_choice == "bat":
                        # losing bowls 1st -> bats 2nd
                        profit = c_bat
                    else:
                        # losing bats 1st -> bowls 2nd
                        profit = c_bowl
            else:
                # non-subs still get their full ALL score
                profit = max(c_all, c_bowl, c_bat)

        else:
            # unknown type -> skip
            continue

        # zero out substitutes who would come in for the innings they cannot contribute to
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

    # keep only the highest-scoring substitute per team
    to_remove = set()
    for team_ini, subs in subs_by_team.items():
        if len(subs) > 1:
            best_name, _ = max(subs, key=lambda x: x[1])
            for name, _ in subs:
                if name != best_name:
                    to_remove.add(name)

    players = [p for p in players if p.name not in to_remove]

    return players


def select_team(players: List[Player], max_weight: float = 100, max_players: int = 11,
                type_limits: dict = DEFAULT_TYPE_LIMITS):
    """Exact constrained knapsack. Returns (best total predicted points, list of player names)."""
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

    return best_profit, best_team


def solve(players: List[Player], df_match_players: pd.DataFrame, out_csv=OUTPUT_CSV,
          max_weight: float = 100, max_players: int = 11, type_limits: dict = DEFAULT_TYPE_LIMITS):
    """Pick the XI, make the top two predicted scorers captain and vice-captain, and save it."""
    _, best_team = select_team(players, max_weight, max_players, type_limits)
    if not best_team:
        raise ValueError("No valid team satisfies the credit, role and team constraints")

    # sort the 11 by predicted points descending
    profit_map = {pl.name: pl.profit for pl in players}
    sorted_team = sorted(best_team, key=lambda n: profit_map[n], reverse=True)
    team_map = df_match_players.set_index("Player Name")["Team"].to_dict()

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

    out_df = pd.DataFrame(rows)
    out_df.to_csv(out_csv, index=False)
    return out_df
