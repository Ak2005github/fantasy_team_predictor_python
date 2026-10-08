"""Run the whole pipeline offline: every website is replaced by ``tests/fake_web.py``.

The run happens in a temporary copy of the data files, so the repository's
own data is never modified.
"""
import os
import shutil
import time

import pandas as pd
import pytest
import requests

from fantasy_predictor import pipeline
from tests.fake_web import FakeWeb

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILES = ["Final_id_data_all.csv", "ipl_2025_matches.csv", "ipl_2025_matches_corrected.csv",
              "ipl_2025_points_table.csv", "ipl_match_dates.csv", "data/SquadPlayerNames_IndianT20League.xlsx"]
MATCH = 30


@pytest.mark.slow
def test_pipeline_picks_a_valid_team(tmp_path, monkeypatch):
    for rel in DATA_FILES:
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(os.path.join(REPO, rel), tmp_path / rel)
    squad = pd.read_excel(tmp_path / "data/SquadPlayerNames_IndianT20League.xlsx", sheet_name=f"Match_{MATCH}")
    (tmp_path / "data" / "resume.flag").touch()  # skip the pause between step 1 and step 2

    web = FakeWeb(REPO)
    monkeypatch.setattr(requests, "get", web.get)
    monkeypatch.setattr(time, "sleep", lambda *_: None)
    monkeypatch.setenv("CRICAPI_KEY", "test-key")
    monkeypatch.chdir(tmp_path)

    pipeline.run(MATCH)

    team = pd.read_csv(tmp_path / "data" / "Ignitors_output.csv", keep_default_na=False)
    assert len(team) == 11
    assert list(team["C/VC"][:2]) == ["C", "VC"]

    picked = squad.set_index("Player Name").loc[team["Player name"]]
    assert picked["Credits"].sum() <= 100
    assert set(picked["IsPlaying"]) <= {"PLAYING", "X_FACTOR_SUBSTITUTE"}
    assert picked["Team"].nunique() == 2
    for role in ["BAT", "BOWL", "WK", "ALL"]:
        assert (picked["Player Type"] == role).any()

    assert not (tmp_path / "data" / "resume.flag").exists()
    assert any("api.cricapi.com/v1/match_info" in url and "test-key" in url for url in web.calls)
