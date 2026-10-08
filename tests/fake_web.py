"""Deterministic offline stand-in for every website the pipeline calls.

It serves synthetic but structurally faithful pages for ESPNcricinfo
(player search, per-player innings tables, ground pages), Cricbuzz
(season fixtures), CricAPI (series and match info) and Wikipedia
(points table). Reference data (squads, fixtures, points table) is read
from a pristine copy of the repository so both the original script and
the refactored pipeline see byte-identical responses.
"""
import json
import os
import random
import re
import zlib
from datetime import date, datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

import pandas as pd

PLAYOFF_IDS = {
    "1c2f9a38-4c3a-407b-90c1-9b78dee63cb8": 71,
    "40596379-a096-4513-8b6f-41df069ca70c": 72,
    "08b32e61-9c96-4f37-8f76-0b3439a80567": 73,
    "b70371b1-6528-4af6-992c-e880ed585183": 74,
}

DISCREPANCY_NAMES = {
    "Andre Siddharth", "Madhav Tiwari", "Manvanth Kumar L", "Mohit Sharma",
    "Lokesh Rahul", "Gurnoor Brar Singh", "Arshad Khan", "Ravisrinivasan Sai Kishore",
    "Rashid-Khan", "Anukul Sudhakar Roy", "Digvesh Singh", "Prince Yadav",
    "Mayank Yadav", "Abdul Samad", "Shahbaz Ahmed", "Mohsin Khan", "Raj Angad Bawa",
    "Ashwani Kumar", "Mujeeb-ur-Rahman", "Rohit Sharma", "Musheer Khan",
    "Harnoor Singh Pannu", "Vyshak Vijaykumar", "Pravin Dubey", "Yash Thakur",
    "Abhinandan Singh", "Philip Salt", "Ashok Sharma", "Yudhvir Singh Charak",
    "Sandeep Sharma", "K Nitish Reddy", "Simarjeet- Singh", "Abhishek Sharma",
}

EXTRA_GROUNDS = ["Sharjah", "Dubai (DSC)", "Abu Dhabi", "Lord's", "Pallekele", "Mirpur"]


class FakeResponse:
    def __init__(self, text="", status_code=200, payload=None):
        self.text = text
        self.status_code = status_code
        self._payload = payload

    def json(self):
        if self._payload is None:
            return json.loads(self.text)
        return self._payload

    def __repr__(self):
        return f"<FakeResponse [{self.status_code}]>"


def _seed(*parts):
    return zlib.crc32("|".join(str(p) for p in parts).encode())


class FakeWeb:
    def __init__(self, ref_dir, toss_missing_for=(), title_mismatch_for=()):
        self.ref_dir = ref_dir
        self.toss_missing_for = set(toss_missing_for)
        self.title_mismatch_for = set(title_mismatch_for)
        self.calls = []

        ids = pd.read_csv(os.path.join(ref_dir, "Final_id_data_all.csv"))
        self.name_to_id = dict(zip(ids["Player Name"], ids["PlayerID"].astype(int)))

        self.matches = pd.read_csv(os.path.join(ref_dir, "ipl_2025_matches_corrected.csv"))
        self.raw_matches = pd.read_csv(os.path.join(ref_dir, "ipl_2025_matches.csv"))
        self.points = pd.read_csv(os.path.join(ref_dir, "ipl_2025_points_table.csv"))

        venues = list(dict.fromkeys(self.matches["Venue"].tolist()))
        self.grounds = {}  # gid -> (short name, full name)
        for i, v in enumerate(venues):
            self.grounds[100000 + i] = (v.split(",")[0].strip(), v)
        for j, g in enumerate(EXTRA_GROUNDS):
            self.grounds[200000 + j] = (g, f"{g} Cricket Ground, {g}")
        self.venue_to_gid = {full: gid for gid, (_, full) in self.grounds.items()}

        self.ipl_days = []
        for _, m in self.matches.iterrows():
            d = datetime.strptime(m["Date"], "%d-%m-%Y").date()
            self.ipl_days.append((d, self.venue_to_gid[m["Venue"]]))

    # ------------------------------------------------------------------ routing
    def get(self, url, headers=None, timeout=None, **kwargs):
        self.calls.append(url)
        if "stats.espncricinfo.com/ci/engine/stats/analysis.html" in url:
            return self._search(url)
        if "stats.espncricinfo.com/ci/engine/player/" in url:
            return self._player(url)
        if "stats.espncricinfo.com/ci/engine/ground/" in url:
            return self._ground(url)
        if "cricbuzz.com" in url:
            return self._cricbuzz()
        if "api.cricapi.com/v1/series_info" in url:
            return self._series()
        if "api.cricapi.com/v1/match_info" in url:
            return self._match_info(url)
        if "wikipedia.org" in url:
            return self._wikipedia()
        raise AssertionError(f"Unexpected URL requested: {url}")

    # ----------------------------------------------------------- ESPNcricinfo
    def player_id_for(self, name):
        if name in self.name_to_id:
            return int(self.name_to_id[name])
        return 9000000 + _seed(name) % 900000

    def _search(self, url):
        m = re.search(r"search=([^;]*);", url)
        name = m.group(1).replace("+", " ")
        pid = self.player_id_for(name)
        links = [pid]
        if name in DISCREPANCY_NAMES:
            links.append(pid + 7)  # ambiguous search result, resolved by the manual map
        anchors = "".join(
            f'<a class="statsLinks" href="/ci/engine/player/{p}.html?class=6;template=results">{name}</a>'
            for p in links
        )
        html = f'<html><body><div id="gurusearch_player">{anchors}</div></body></html>'
        return FakeResponse(html)

    def _innings_plan(self, pid):
        rng = random.Random(_seed("plan", pid))
        days = []
        start = date(2022, 3, 1)
        for k in range(rng.randint(30, 55)):
            d = start + timedelta(days=rng.randint(0, 1000))
            if d.year == 2025 and d.month in (3, 4, 5, 6):
                continue  # IPL 2025 days are added below with their real venue
            gid = rng.choice(list(self.grounds))
            days.append((d, gid))
        for d, gid in self.ipl_days:
            if rng.random() < 0.6:
                days.append((d, gid))
        days = sorted(set(days))
        plan = []
        for d, gid in days:
            plan.append({
                "date": d,
                "gid": gid,
                "inns": rng.choice([1, 2]),
                "opp_tid": rng.choice([4340, 4341, 4342, 4343, 4344, 4345]),
            })
        return plan

    @staticmethod
    def _fmt_date(d):
        return f"{d.day} {d.strftime('%b')} {d.year}"

    def _common_cells(self, ev):
        short, _ = self.grounds[ev["gid"]]
        opp = f'<td><a href="/ci/content/team/{ev["opp_tid"]}.html">v Team{ev["opp_tid"]}</a></td>'
        ground = f'<td><a href="/ci/engine/ground/{ev["gid"]}.html">{short}</a></td>'
        start = f'<td>{self._fmt_date(ev["date"])}</td>'
        return opp, ground, start

    def _table_page(self, header, rows):
        dummy = '<table class="engineTable"><tr><th>x</th></tr><tr><td>1</td></tr></table>'
        ths = "".join(f"<th>{h}</th>" for h in header)
        body = "".join("<tr>" + "".join(r) + "</tr>" for r in rows)
        target = f'<table class="engineTable"><tr>{ths}</tr>{body}</table>'
        return FakeResponse(f"<html><body>{dummy * 3}{target}</body></html>")

    def _player(self, url):
        pid = int(re.search(r"/player/(\d+)\.html", url).group(1))
        q = url.split("?", 1)[1]
        plan = self._innings_plan(pid)
        rng = random.Random(_seed("stats", pid, q))
        if "type=batting" in q:
            return self._batting(plan, rng)
        if "view=dismissal_list" in q:
            return self._dismissals(pid, plan)
        if "type=bowling" in q:
            return self._bowling(pid, plan, rng)
        if "type=fielding" in q:
            return self._fielding(plan, rng)
        raise AssertionError(url)

    def _batting(self, plan, rng):
        header = ["Runs", "Mins", "BF", "4s", "6s", "SR", "Pos", "Dismissal", "Inns", "",
                  "Opposition", "Ground", "Start Date", ""]
        rows = []
        for ev in plan:
            opp, ground, start = self._common_cells(ev)
            r = rng.random()
            if r < 0.04:
                cells = ["TDNB"] + ["-"] * 6 + ["-", str(ev["inns"])]
            elif r < 0.14:
                cells = ["DNB"] + ["-"] * 6 + ["-", str(ev["inns"])]
            else:
                bf = rng.randint(1, 60)
                runs = max(0, int(bf * rng.uniform(0.5, 2.1)))
                fours = rng.randint(0, max(0, runs // 8))
                sixes = rng.randint(0, max(0, runs // 15))
                sr = f"{runs / bf * 100:.2f}"
                notout = rng.random() < 0.15
                cells = [f"{runs}*" if notout else str(runs), str(bf + rng.randint(0, 20)), str(bf),
                         str(fours), str(sixes), sr, str(rng.randint(1, 9)),
                         "not out" if notout else rng.choice(["caught", "bowled", "lbw", "run out"]),
                         str(ev["inns"])]
            rows.append([f"<td>{c}</td>" for c in cells] + ["<td></td>", opp, ground, start, "<td></td>"])
        return self._table_page(header, rows)

    def _bowling_events(self, pid, plan):
        rng = random.Random(_seed("bowl", pid))
        out = []
        for ev in plan:
            r = rng.random()
            if r < 0.04:
                out.append((ev, None))
                continue
            balls = rng.randint(6, 24)
            overs = f"{balls // 6}" if balls % 6 == 0 else f"{balls // 6}.{balls % 6}"
            runs = int(balls * rng.uniform(0.7, 2.2))
            wkts = min(5, max(0, int(rng.gauss(1.0, 1.1))))
            mdns = 1 if (balls >= 6 and rng.random() < 0.05) else 0
            econ = f"{runs / (balls / 6):.2f}"
            out.append((ev, dict(overs=overs, balls=balls, runs=runs, wkts=wkts, mdns=mdns, econ=econ,
                                 pos=rng.randint(1, 6))))
        return out

    def _bowling(self, pid, plan, rng):
        with_bpo = pid % 3 == 0
        header = ["Overs"] + (["BPO"] if with_bpo else []) + ["Mdns", "Runs", "Wkts", "Econ", "Pos", "Inns", "",
                                                                "Opposition", "Ground", "Start Date", ""]
        rows = []
        for ev, s in self._bowling_events(pid, plan):
            opp, ground, start = self._common_cells(ev)
            if s is None:
                cells = ["TDNB"] + (["-"] if with_bpo else []) + ["-"] * 5 + [str(ev["inns"])]
            else:
                cells = [s["overs"]] + (["6"] if with_bpo else []) + [str(s["mdns"]), str(s["runs"]),
                                                                      str(s["wkts"]), s["econ"], str(s["pos"]),
                                                                      str(ev["inns"])]
            rows.append([f"<td>{c}</td>" for c in cells] + ["<td></td>", opp, ground, start, "<td></td>"])
        return self._table_page(header, rows)

    def _dismissals(self, pid, plan):
        header = ["Batter", "How out", "Fielder", "Runs", "Inns", "Opposition", "Ground", "Start Date"]
        rows = []
        rng = random.Random(_seed("wic", pid))
        for ev, s in self._bowling_events(pid, plan):
            if not s or not s["wkts"]:
                continue
            opp, ground, start = self._common_cells(ev)
            for w in range(s["wkts"]):
                how = rng.choice(["caught", "caught", "bowled", "lbw", "run out"])
                cells = [f"Batter{w}", how, "-", str(rng.randint(0, 70)), str(ev["inns"])]
                rows.append([f"<td>{c}</td>" for c in cells] + [opp, ground, start])
        return self._table_page(header, rows)

    def _fielding(self, plan, rng):
        header = ["Dis", "Ct", "St", "Ct Wk", "Ct Fi", "Inns", "", "Opposition", "Ground", "Start Date", ""]
        rows = []
        for ev in plan:
            opp, ground, start = self._common_cells(ev)
            if rng.random() < 0.03:
                cells = ["TDNF", "-", "-", "-", "-", str(ev["inns"])]
            else:
                ct = rng.choice([0, 0, 0, 1, 1, 2, 3])
                st = 1 if rng.random() < 0.03 else 0
                cells = [str(ct + st), str(ct), str(st), "0", str(ct), str(ev["inns"])]
            rows.append([f"<td>{c}</td>" for c in cells] + ["<td></td>", opp, ground, start, "<td></td>"])
        return self._table_page(header, rows)

    def _ground(self, url):
        gid = int(re.search(r"/ground/(\d+)\.html", url).group(1))
        _, full = self.grounds[gid]
        html = (f'<html><body><a href="/records">Statsguru / {full} / Twenty20 matches</a>'
                f"</body></html>")
        return FakeResponse(html)

    # ---------------------------------------------------------------- Cricbuzz
    def _cricbuzz(self):
        blocks = []
        for _, m in self.raw_matches.iterrows():
            dt = datetime.strptime(m["Date (UTC)"], "%Y-%m-%d %A %I:%M %p").replace(tzinfo=timezone.utc)
            ms = int(dt.timestamp() * 1000)
            result = "" if pd.isna(m["Result"]) else m["Result"]
            blocks.append(
                '<div class="cb-col-75 cb-col">'
                f'<span>{m["Match Title"]}</span>'
                f'<div class="text-gray">{m["Venue"]}</div>'
                f'<a class="cb-text-complete">{result}</a>'
                f'<div class="cb-font-12 text-gray">{m["Raw Time (GMT/Local)"]}</div>'
                f'<span timestamp="{ms}"></span>'
                "</div>"
            )
        return FakeResponse("<html><body>" + "".join(blocks) + "</body></html>")

    # ------------------------------------------------------------------ CricAPI
    def _cricapi_id(self, number):
        return f"fake-match-{int(number):03d}"

    def _series(self):
        match_list = []
        for _, m in self.matches.iterrows():
            num = int(m["Match Number"])
            if num in PLAYOFF_IDS.values():
                mid = next(k for k, v in PLAYOFF_IDS.items() if v == num)
            else:
                mid = self._cricapi_id(num)
            d = datetime.strptime(m["Date"], "%d-%m-%Y").strftime("%Y-%m-%d")
            name = m["Match Title"]
            if num in self.title_mismatch_for:
                name = name.replace(" vs ", " v ")  # title lookup fails, number lookup still works
            match_list.append({"id": mid, "name": name, "date": d})
        return FakeResponse(payload={"status": "success", "data": {"matchList": match_list}})

    def _match_info(self, url):
        mid = parse_qs(urlparse(url).query)["id"][0]
        if mid in PLAYOFF_IDS:
            num = PLAYOFF_IDS[mid]
        else:
            num = int(mid.rsplit("-", 1)[1])
        m = self.matches[self.matches["Match Number"] == num].iloc[0]
        teams = m["Match Title"].split(",")[0].split(" vs ")
        rng = random.Random(_seed("toss", num))
        data = {
            "id": mid,
            "name": m["Match Title"],
            "venue": m["Venue"],
            "date": datetime.strptime(m["Date"], "%d-%m-%Y").strftime("%Y-%m-%d"),
        }
        if num not in self.toss_missing_for:
            data["tossWinner"] = rng.choice(teams)
            data["tossChoice"] = rng.choice(["bat", "bowl"])
        return FakeResponse(payload={"status": "success", "data": data})

    # --------------------------------------------------------------- Wikipedia
    def _wikipedia(self):
        cols = list(self.points.columns)
        head = "<tr>" + "".join(f"<th>{c}</th>" for c in cols) + "</tr>"
        body = ""
        for _, r in self.points.iterrows():
            vals = ["" if pd.isna(v) else v for v in r.tolist()]
            body += "<tr><th>" + str(vals[0]) + "</th>" + "".join(f"<td>{v}</td>" for v in vals[1:]) + "</tr>"
        html = ('<html><body><table class="wikitable module-CricketLeagueGroupStageSummary">'
                f"{head}{body}</table></body></html>")
        return FakeResponse(html)
