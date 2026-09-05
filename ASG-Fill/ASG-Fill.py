"""
Fills an OOTP All-Star ballot template from vote results exported from OOTP
(votes.json). Top vote-getter(s) at each position become the starter(s); the
next highest vote-getter(s) become reserves.

This project includes built-in profiles for AFBL and NPBL, but the logic is
intended to work for other leagues using either common OOTP roster setup:
LF/CF/RF + DH or 3 OF + no DH. The roster shape is auto-detected from the
"league" field in votes.json, and new league profiles can be added via the
PROFILES mapping.

On a tie, you're prompted to pick manually. If a StatsPlus API token is
available, each tied candidate's season stats (via playerbatstatsv2 /
playerpitchstatsv2) are shown to help decide.

Usage:
    python ASG-Fill.py path/to/votes.json [-o output.txt] [--token TOKEN]
"""
import argparse
import csv
import json
import os
from collections import defaultdict

import requests

# Each entry: (json position key, template label, slot count)
PROFILES = {
    "AFBL": {
        "batting": [
            ("C", "CA", 1), ("1B", "1B", 1), ("2B", "2B", 1), ("3B", "3B", 1), ("SS", "SS", 1),
            ("LF", "LF", 1), ("CF", "CF", 1), ("RF", "RF", 1),
        ],
        "dh": True,
    },
    "NPBL": {
        "batting": [
            ("C", "CA", 1), ("1B", "1B", 1), ("2B", "2B", 1), ("3B", "3B", 1), ("SS", "SS", 1),
            ("OF", "OF", 3),
        ],
        "dh": False,
    },
}
DEFAULT_PROFILE = "AFBL"

PITCHING_POSITIONS = ("SP", "RP")
SP_RESERVE_SLOTS = 5
RP_RESERVE_SLOTS = 6
# A reserve/backup can't be filled by a player with only 1 vote; leave it blank for a manual pick
MIN_RESERVE_VOTES = 2

STATSPLUS_BASE = "https://statsplus.net/{league}/api/{endpoint}/"


def get_profile(league):
    return PROFILES.get(league.upper(), PROFILES[DEFAULT_PROFILE])


def format_player(player):
    if not player:
        return ""
    text = f"{player['name']} ({player['teams']})"
    if player["votes"] == player.get("ballots"):
        text += f" [unanimous {player['votes']}/{player['ballots']}]"
    return text


def _num(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _sum_field(rows, field):
    return sum(_num(row.get(field)) for row in rows)


def _fmt_rate(value):
    """Formats a batting rate stat to 3 decimals without the leading zero (e.g. .300)."""
    text = f"{value:.3f}"
    return text[1:] if text.startswith("0.") else text


def batter_stat_line(rows, wrc_plus=None):
    ab = _sum_field(rows, "ab")
    if not ab:
        return None
    h = _sum_field(rows, "h")
    doubles = _sum_field(rows, "d")
    triples = _sum_field(rows, "t")
    hr = _sum_field(rows, "hr")
    bb = _sum_field(rows, "bb")
    hp = _sum_field(rows, "hp")
    sf = _sum_field(rows, "sf")
    rbi = _sum_field(rows, "rbi")
    war = _sum_field(rows, "war")

    avg = h / ab
    obp_den = ab + bb + hp + sf
    obp = (h + bb + hp) / obp_den if obp_den else 0.0
    singles = h - doubles - triples - hr
    total_bases = singles + 2 * doubles + 3 * triples + 4 * hr
    slg = total_bases / ab
    ops = obp + slg
    wrc_suffix = f", {wrc_plus:.0f} wRC+" if wrc_plus is not None else ""
    return (f"{_fmt_rate(avg)}/{_fmt_rate(obp)}/{_fmt_rate(slg)} ({_fmt_rate(ops)} OPS), "
            f"{int(hr)} HR, {int(rbi)} RBI, {war:.1f} WAR{wrc_suffix}")


def pitcher_stat_line(rows):
    outs = _sum_field(rows, "outs")
    if not outs:
        return None
    w = _sum_field(rows, "w")
    losses = _sum_field(rows, "l")
    er = _sum_field(rows, "er")
    k = _sum_field(rows, "k")
    wpa = _sum_field(rows, "wpa")
    war = _sum_field(rows, "war")

    era = er * 27 / outs
    ip_whole, ip_thirds = divmod(int(outs), 3)
    return (f"{int(w)}-{int(losses)}, {era:.2f} ERA, {ip_whole}.{ip_thirds} IP, "
            f"{int(k)} K, {wpa:.2f} WPA, {war:.1f} WAR")


_UNSET = object()


class StatsClient:
    """Looks up season stats from the StatsPlus API to help break voting ties.

    wRC+ is approximated: FanGraphs derives wOBA weights/scale from a full run-value
    regression, which isn't reproducible from box-score totals alone, so fixed
    modern-MLB-average constants are used instead of league/year-specific ones.
    """

    WOBA_WEIGHTS = {"bb": 0.69, "hbp": 0.72, "single": 0.89, "double": 1.27, "triple": 1.62, "hr": 2.10}
    WOBA_SCALE = 1.15

    def __init__(self, league, year, token, enabled=True):
        self.league = league
        self.year = year
        self.token = token
        self.enabled = enabled and bool(token)
        self._cache = {}
        self._league_totals = _UNSET
        self._warned = set()

    def get_line(self, player, position):
        if not self.enabled:
            return None
        key = (player.get("player_id"), position)
        if key in self._cache:
            return self._cache[key]

        if position in PITCHING_POSITIONS:
            rows = self._fetch(player.get("player_id"), "playerpitchstatsv2")
            line = pitcher_stat_line(rows)
        else:
            rows = self._fetch(player.get("player_id"), "playerbatstatsv2")
            line = batter_stat_line(rows, wrc_plus=self._wrc_plus(rows))

        self._cache[key] = line
        return line

    def _warn(self, message):
        if message not in self._warned:
            print(f"  ({message})")
            self._warned.add(message)

    def _fetch(self, player_id, endpoint):
        url = STATSPLUS_BASE.format(league=self.league.lower(), endpoint=endpoint)
        try:
            resp = requests.get(
                url, params={"pid": player_id, "year": self.year, "token": self.token}, timeout=10
            )
            resp.raise_for_status()
        except requests.RequestException as e:
            self._warn(f"StatsPlus lookup unavailable: {e}")
            return []

        text_lines = resp.text.strip().splitlines()
        if len(text_lines) < 2:
            return []
        # split_id 1 is the full-season total row (2/3+ are platoon splits)
        return [row for row in csv.DictReader(text_lines) if row.get("split_id") == "1"]

    def _woba(self, ab, bb, ibb, hp, h, doubles, triples, hr, sf):
        den = ab + bb - ibb + sf + hp
        if den <= 0:
            return None
        singles = h - doubles - triples - hr
        w = self.WOBA_WEIGHTS
        num = (w["bb"] * (bb - ibb) + w["hbp"] * hp + w["single"] * singles
               + w["double"] * doubles + w["triple"] * triples + w["hr"] * hr)
        return num / den

    def _get_league_totals(self):
        """Returns (league wOBA, league R/PA), cached per league/year."""
        if self._league_totals is not _UNSET:
            return self._league_totals

        url = STATSPLUS_BASE.format(league=self.league.lower(), endpoint="teambatstats")
        try:
            resp = requests.get(url, params={"year": self.year, "token": self.token}, timeout=10)
            resp.raise_for_status()
            lines = resp.text.strip().splitlines()
            rows = list(csv.DictReader(lines)) if len(lines) >= 2 else []
        except requests.RequestException as e:
            self._warn(f"league batting totals unavailable: {e}")
            rows = []

        ab, bb, ibb, hp, h, d, t, hr, sf, pa, r = (
            _sum_field(rows, f) for f in ("ab", "bb", "ibb", "hp", "h", "d", "t", "hr", "sf", "pa", "r")
        )
        lg_woba = self._woba(ab, bb, ibb, hp, h, d, t, hr, sf)
        lg_r_pa = r / pa if pa else None
        self._league_totals = (lg_woba, lg_r_pa) if lg_woba and lg_r_pa else None
        return self._league_totals

    def _wrc_plus(self, rows):
        """wRC+ isn't park-adjusted: StatsPlus's own displayed values line up much
        more closely without a park factor than with one, for this league."""
        league = self._get_league_totals()
        if not league:
            return None
        lg_woba, lg_r_pa = league

        pa = _sum_field(rows, "pa")
        if not pa:
            return None
        ab, bb, ibb, hp, h, d, t, hr, sf = (
            _sum_field(rows, f) for f in ("ab", "bb", "ibb", "hp", "h", "d", "t", "hr", "sf")
        )
        player_woba = self._woba(ab, bb, ibb, hp, h, d, t, hr, sf)
        if player_woba is None:
            return None

        wraa_per_pa = (player_woba - lg_woba) / self.WOBA_SCALE
        return (wraa_per_pa + lg_r_pa) / lg_r_pa * 100


def _print_candidate(index, player, position, stats):
    line = stats.get_line(player, position) if stats else None
    suffix = f" — {line}" if line else ""
    print(f"  {index}. {player['name']} ({player['teams']}){suffix}")


def resolve_starter_ties(players, slots, context_label, position, auto=False, stats=None):
    """Resolves ties among the top `slots` vote-getters (the starter slot(s) for
    this position); keeps bumped tied players in place for reserve consideration."""
    if not players:
        return players

    slot_label = "starter" if slots == 1 else "starters"
    return _resolve_tie_slots(players, slots, context_label, position, auto=auto, stats=stats, slot_label=slot_label)


def _describe(players):
    return ", ".join(f"{p['name']} ({p['votes']} vote{'s' if p['votes'] != 1 else ''})" for p in players)


def _group_by_votes(players):
    groups = []
    for p in players:
        if groups and groups[-1][0]["votes"] == p["votes"]:
            groups[-1].append(p)
        else:
            groups.append([p])
    return groups


def _resolve_tie_slots(players, slots, context_label, position, auto=False, stats=None, slot_label=""):
    """Fills the top `slots` spots from a vote-sorted list, prompting whenever a
    tied group would otherwise straddle the cutoff, and leaves the rest in order."""
    chosen_count = 0
    result = []
    for group in _group_by_votes(players):
        needed = slots - chosen_count
        if needed <= 0 or len(group) <= needed:
            result.extend(group)
            chosen_count += len(group)
            continue
        picked = choose_tied_group(group, needed, context_label, position, auto=auto, stats=stats, slot_label=slot_label)
        others = [p for p in group if p not in picked]
        result.extend(picked + others)
        chosen_count += len(picked)
    return result


def choose_tied_group(group, count, context_label, position, auto=False, stats=None, slot_label=""):
    """Prompt to pick `count` players out of a vote-tied group for the remaining slot(s)."""
    votes = group[0]["votes"]
    slot_word = "spot" if count == 1 else "spots"
    heading = f"{context_label} {slot_label}".strip()
    print(f"\nTie for {heading} ({votes} votes each, {count} {slot_word} open of {len(group)} tied):")
    for i, p in enumerate(group, start=1):
        _print_candidate(i, p, position, stats)

    if auto:
        print(f"  -> auto mode: keeping first {count} listed")
        return group[:count]

    prompt_word = "starter" if slot_label.startswith("starter") else "reserve"
    remaining = list(group)
    chosen = []
    while len(chosen) < count:
        choice = input(f"Select {prompt_word} #{len(chosen) + 1} for {heading} [1-{len(remaining)}]: ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(remaining):
            chosen.append(remaining.pop(int(choice) - 1))
        else:
            print("Invalid selection, try again.")
    return chosen


def pick_reserves(candidates, slots, context_label, position, auto=False, stats=None, manual_review=None):
    """Fills up to `slots` reserves from candidates meeting MIN_RESERVE_VOTES,
    prompting on ties at the cutoff and leaving unmet slots blank for manual review."""
    eligible = [p for p in candidates if p["votes"] >= MIN_RESERVE_VOTES]
    below_threshold = [p for p in candidates if p["votes"] < MIN_RESERVE_VOTES]

    chosen = []
    for group in _group_by_votes(eligible):
        remaining_slots = slots - len(chosen)
        if remaining_slots <= 0:
            break
        if len(group) <= remaining_slots:
            chosen.extend(group)
        else:
            chosen.extend(choose_tied_group(group, remaining_slots, context_label, position, auto=auto, stats=stats))

    unmet = slots - len(chosen)
    if unmet > 0:
        if below_threshold:
            reason = f"remaining ballot below {MIN_RESERVE_VOTES}-vote minimum: {_describe(below_threshold)}"
        else:
            reason = "no other candidates received votes (unanimous starter selected)"
        print(f"Note: {context_label} needs manual review - {reason}")
        if manual_review is not None:
            slot_word = "slot" if unmet == 1 else "slots"
            manual_review.append(f"{context_label} ({unmet} {slot_word} unmet) - {reason}")
    return chosen


def load_votes(votes_path):
    with open(votes_path, encoding="utf-8") as f:
        data = json.load(f)

    # league -> sub_league -> position -> [players sorted by votes desc]
    leagues = defaultdict(lambda: defaultdict(dict))
    year = None
    for entry in data["results"]:
        year = entry["year"]
        players = sorted(entry["players"], key=lambda p: p["votes"], reverse=True)
        for p in players:
            p["ballots"] = entry["ballots"]
        leagues[entry["league"]][entry["sub_league"]][entry["position"]] = players

    return leagues, year


def build_section(players_by_pos, context_label, profile, auto=False, stats=None, manual_review=None):
    lines = ["_Starters_"]
    for pos_key, tmpl_label, count in profile["batting"]:
        players = players_by_pos.get(pos_key, [])
        for i in range(count):
            lines.append(f"{tmpl_label}: {format_player(players[i] if i < len(players) else None)}")

    if profile["dh"]:
        dh = players_by_pos.get("DH", [])
        lines.append(f"DH: {format_player(dh[0] if dh else None)}")

    sp = players_by_pos.get("SP", [])
    lines.append(f"SP: {format_player(sp[0] if sp else None)}")

    lines.append("")
    lines.append("_Reserves_")
    for pos_key, tmpl_label, count in profile["batting"]:
        players = players_by_pos.get(pos_key, [])
        reserves = pick_reserves(
            players[count:], count, f"{context_label} {tmpl_label} reserve", pos_key,
            auto=auto, stats=stats, manual_review=manual_review
        )
        for i in range(count):
            lines.append(f"{tmpl_label}: {format_player(reserves[i] if i < len(reserves) else None)}")

    sp_reserves = pick_reserves(
        sp[1:], SP_RESERVE_SLOTS, f"{context_label} SP reserve", "SP",
        auto=auto, stats=stats, manual_review=manual_review
    )
    for i in range(SP_RESERVE_SLOTS):
        player = sp_reserves[i] if i < len(sp_reserves) else None
        lines.append(f"SP: {format_player(player)}")

    rp_reserves = pick_reserves(
        players_by_pos.get("RP", []), RP_RESERVE_SLOTS, f"{context_label} RP reserve", "RP",
        auto=auto, stats=stats, manual_review=manual_review
    )
    for i in range(RP_RESERVE_SLOTS):
        player = rp_reserves[i] if i < len(rp_reserves) else None
        lines.append(f"RP: {format_player(player)}")

    return lines


def resolve_all_ties(sub_leagues, league, auto=False, stats=None):
    profile = get_profile(league)
    for sub_league, players_by_pos in sub_leagues.items():
        for pos_key, tmpl_label, count in profile["batting"]:
            if pos_key not in players_by_pos:
                continue
            context_label = f"{league} {sub_league} {tmpl_label}"
            players_by_pos[pos_key] = resolve_starter_ties(
                players_by_pos[pos_key], count, context_label, pos_key, auto=auto, stats=stats
            )

        if profile["dh"] and "DH" in players_by_pos:
            context_label = f"{league} {sub_league} DH"
            players_by_pos["DH"] = resolve_starter_ties(
                players_by_pos["DH"], 1, context_label, "DH", auto=auto, stats=stats
            )

        if "SP" in players_by_pos:
            context_label = f"{league} {sub_league} SP"
            players_by_pos["SP"] = resolve_starter_ties(
                players_by_pos["SP"], 1, context_label, "SP", auto=auto, stats=stats
            )


def build_league_text(sub_leagues, year, league, auto=False, stats=None, manual_review=None):
    profile = get_profile(league)
    lines = [f"*{year} All-Star Game Selections*"]
    for sub_league, players_by_pos in sub_leagues.items():
        lines.append(f"*{sub_league}*")
        lines.extend(build_section(
            players_by_pos, f"{league} {sub_league}", profile, auto=auto, stats=stats, manual_review=manual_review
        ))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main():
    parser = argparse.ArgumentParser(
        description="Fill an OOTP ASG ballot template from votes.json (supports AFBL and NPBL roster formats)"
    )
    parser.add_argument("votes_path", help="Path to the votes.json export")
    parser.add_argument("-o", "--output", help="Output file path (single-league mode only)")
    parser.add_argument("--auto", action="store_true",
                        help="Don't prompt on ties; auto-pick the first tied player")
    parser.add_argument("--token", help="StatsPlus API token (defaults to STATSPLUS_API_KEY env var)")
    parser.add_argument("--no-stats", action="store_true",
                        help="Don't look up StatsPlus stats to help break ties")
    args = parser.parse_args()

    token = args.token or os.environ.get("STATSPLUS_API_KEY")
    if not args.no_stats and not token:
        print("Note: no StatsPlus API token found (set STATSPLUS_API_KEY or pass --token); "
              "tie prompts won't show stats.")

    leagues, year = load_votes(args.votes_path)

    for league, sub_leagues in leagues.items():
        stats = StatsClient(league, year, token, enabled=not args.no_stats)
        manual_review = []
        resolve_all_ties(sub_leagues, league, auto=args.auto, stats=stats)
        text = build_league_text(sub_leagues, year, league, auto=args.auto, stats=stats, manual_review=manual_review)
        out_path = args.output or f"{league}-ASG-{year}.txt"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"Wrote {out_path}")

        print(f"\nManual Selections Needed ({league}):")
        if manual_review:
            for entry in manual_review:
                print(f"  - {entry}")
        else:
            print("  (none)")


if __name__ == "__main__":
    main()
