# IPL Fantasy XI Predictor

Predicts the best Dream11 fantasy XI for an IPL 2025 match. Built for the FIFS Gameathon 2.0 (Dream11), where the team **Ignitors** finished as national winners (top 10 of 650+ teams).

The pipeline scrapes each squad player's T20 history, scores every past innings with Dream11's T20 rules, trains CatBoost models to predict each player's fantasy points for the match, and then picks the highest-scoring XI that satisfies the game's credit, role and team rules.

## How it works

The run has two steps, because lineups and the toss are only announced shortly before the match.

**Step 1: before the toss**

1. Clean the squad workbook (`squad.py`) and resolve every player to an ESPNcricinfo ID (`player_ids.py`).
2. Download each player's innings-by-innings batting, bowling and fielding records (`scraper.py`).
3. Score every innings with Dream11 T20 rules (`scoring.py`) and align the files (`cleaning.py`, `grounds.py`).
4. Add zero-point rows for matches a player sat out (`substitutes.py`).
5. Build training tables of form-before-each-innings and venue-history features (`features_training.py`).

The run then pauses until the file `data/resume.flag` exists.

**Step 2: after the toss**

6. Fetch the toss result from CricAPI (`cricapi.py`) and work out which innings each team bats in.
7. Train three CatBoost models, for batters, bowlers and all-rounders, and predict every player's points (`features_prediction.py`, `models.py`).
8. Select the XI with an exact dynamic-programming knapsack (`optimizer.py`): 11 players, at most 100 credits, 1-8 batters, 1-4 bowlers, 1-8 keepers, 1-4 all-rounders, and at least one player from each team. The two highest predicted scorers become captain and vice-captain.

The result is saved to `data/Ignitors_output.csv`.

## Setup

Requires Python 3.11.

```bash
pip install -r requirements.txt
export CRICAPI_KEY=<your CricAPI key>
```

The API key is read from the environment and never stored in the code.

## Running

```bash
python -m fantasy_predictor 30          # match number 30; playoffs are 71-74
```

When the console shows `STEP 1 COMPLETE`, wait for the toss, then in a second terminal:

```bash
touch data/resume.flag
```

The pipeline edits the squad workbook and the fixture CSVs in place and writes intermediate files to `Data_players/` and the working directory. To restore the committed versions afterwards, run `git checkout -- data Final_id_data_all.csv ipl_*.csv`.

### With Docker

```bash
docker build -t fantasy-predictor .
docker run --name ipl30 -e CRICAPI_KEY=<your key> fantasy-predictor 30
docker exec ipl30 touch data/resume.flag       # after the toss
docker cp ipl30:/app/data/Ignitors_output.csv .
```

## Tests

```bash
pip install -r requirements-dev.txt
pytest -m "not slow"     # unit tests, about 1 second
pytest -m slow           # full pipeline end to end, about 3 minutes
```

- `test_scoring.py` checks the Dream11 batting, bowling and fielding rules.
- `test_optimizer.py` checks the knapsack against a brute-force search over every possible XI on 30 random squads.
- `test_end_to_end.py` runs the whole pipeline offline: `tests/fake_web.py` stands in for ESPNcricinfo, Cricbuzz, CricAPI and Wikipedia, and the run happens in a temporary copy of the data.

GitHub Actions runs all of these on every push and pull request.

## Project layout

```
fantasy_predictor/      the pipeline, one module per stage (see "How it works")
tests/                  unit tests, end-to-end test and the offline fake web
data/                   squad workbook (input) and predicted team (output)
*.csv                   player IDs, season fixtures and team codes
legacy/                 the original single-script version, kept for reference
```

## Author

Akshith Kasimsetty, [akshith0104@gmail.com](mailto:akshith0104@gmail.com)
