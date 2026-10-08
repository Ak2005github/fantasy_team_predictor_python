"""Small cricket helpers shared by several stages."""


def convert_overs_to_balls(over):
    """Convert overs notation (e.g. 3.4 = 3 overs and 4 balls) to balls bowled; None if unparseable."""
    try:
        over_str = str(over)
        if '.' in over_str:
            parts = over_str.split('.')
            complete_overs = int(parts[0])
            extra_balls = int(parts[1])
        else:
            complete_overs = int(over_str)
            extra_balls = 0
        return complete_overs * 6 + extra_balls
    except Exception:
        return None


def resolve_toss_winner(teams, toss_winner_code):
    """Return which of the two squad team codes won the toss.

    The squad sheet and the points table can use different codes
    (e.g. 'CHE' vs 'CSK'), so fall back to a unique first-letter match.
    """
    if len(teams) != 2:
        raise ValueError(f"Expected exactly 2 unique teams, got {teams}")

    if toss_winner_code in teams:
        return toss_winner_code

    init_char = toss_winner_code[0].lower()
    matches = [t for t in teams if t and t[0].lower() == init_char]
    if len(matches) == 1:
        return matches[0]
    raise ValueError(
        f"Could not resolve winner from initials '{toss_winner_code}' "
        f"against teams {teams}"
    )


def innings_map(teams, toss_winner_code, toss_choice, bowling=False):
    """Map each team to the innings (1 or 2) it bats in, or bowls in when ``bowling`` is True."""
    winner = resolve_toss_winner(teams, toss_winner_code)
    loser = teams[0] if teams[1] == winner else teams[1]

    choice = toss_choice.lower()
    if choice == 'bat':
        winner_bats_first = True
    elif choice == 'bowl':
        winner_bats_first = False
    else:
        raise ValueError("choice_of_win_team must be 'bat' or 'bowl'")

    winner_first = winner_bats_first != bowling
    return {winner: 1, loser: 2} if winner_first else {winner: 2, loser: 1}
