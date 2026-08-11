import argparse
import sys
import xml.etree.ElementTree as ET
from xml.dom import minidom

DAY_MAP = {
    "sunday": 1, "sun": 1, "1": 1,
    "monday": 2, "mon": 2, "2": 2,
    "tuesday": 3, "tue": 3, "3": 3,
    "wednesday": 4, "wed": 4, "4": 4,
    "thursday": 5, "thu": 5, "5": 5,
    "friday": 6, "fri": 6, "6": 6,
    "saturday": 7, "sat": 7, "7": 7,
}

MONTH_MAP = {
    "january": 1, "jan": 1, "1": 1,
    "february": 2, "feb": 2, "2": 2,
    "march": 3, "mar": 3, "3": 3,
    "april": 4, "apr": 4, "4": 4,
    "may": 5, "5": 5,
    "june": 6, "jun": 6, "6": 6,
    "july": 7, "jul": 7, "7": 7,
    "august": 8, "aug": 8, "8": 8,
    "september": 9, "sep": 9, "sept": 9, "9": 9,
    "october": 10, "oct": 10, "10": 10,
    "november": 11, "nov": 11, "11": 11,
    "december": 12, "dec": 12, "12": 12,
}


def get_weekday(day_index, start_day):
    """Calculates the 1-7 (Sun-Sat) weekday integer for any given schedule day."""
    return (start_day - 1 + day_index - 1) % 7 + 1


def decompose_games_to_series(total_games_val):
    """Decomposes a game count per opponent into 3-game, 2-game, and 4-game series."""
    # Safely parse if string "6/7" is passed from the MLB split logic
    if isinstance(total_games_val, str):
        if '/' in total_games_val:
            total_games_per_opp = int(total_games_val.split('/')[0])
        elif total_games_val == "N/A":
            return []
        else:
            total_games_per_opp = int(total_games_val)
    else:
        total_games_per_opp = int(total_games_val)
        
    if total_games_per_opp <= 0:
        return []

    # Hardcoded MLB asymmetrical odd-math configurations
    if total_games_per_opp == 13:
        return [4, 3, 3, 3]
    if total_games_per_opp == 7:
        return [4, 3]
    if total_games_per_opp == 6:
        return [3, 3]
    if total_games_per_opp == 4:
        return [4]
    if total_games_per_opp == 3:
        return [3]

    # Original Fallback for symmetrical/fictional configurations
    half_games = total_games_per_opp // 2
    
    rem = half_games
    num_3g = rem // 3
    rem %= 3

    num_2g = 0
    num_4g = 0

    if rem == 1:
        if num_3g > 0:
            num_3g -= 1
            num_4g += 1
        else:
            num_2g += 1
    elif rem == 2:
        num_2g += 1

    spread = []
    for type_idx, count in enumerate([num_3g, num_4g, num_2g]):
        length = [3, 4, 2][type_idx]
        for i in range(count):
            pos = (i + 0.5) / count if count > 0 else 0
            pos += type_idx * 0.0001
            spread.append((pos, [length, length]))
            
    spread.sort(key=lambda x: x[0])
    
    series_list = []
    for pos, pair in spread:
        series_list.extend(pair)

    return series_list


def generate_circle_rounds(team_list):
    """Generates intra-group round-robin pairings using the Circle Method."""
    n = len(team_list)
    teams = list(team_list)
    if n % 2 != 0:
        teams.append(None)
        n += 1

    rounds = []
    for _ in range(n - 1):
        pairings = [
            (teams[i], teams[n - 1 - i])
            for i in range(n // 2)
            if teams[i] and teams[n - 1 - i]
        ]
        rounds.append(pairings)
        teams = [teams[0]] + [teams[-1]] + teams[1:-1]
    return rounds


def generate_bipartite_rounds(group_a, group_b):
    """Generates cross-group bipartite pairings with 50/50 home/road balancing."""
    n = len(group_a)
    rounds = []
    for r in range(n):
        pairings = []
        for i in range(n):
            t1 = group_a[i]
            t2 = group_b[(i + r) % n]
            if (i + r) % 2 == 0:
                pairings.append((t1, t2))
            else:
                pairings.append((t2, t1))
        rounds.append(pairings)
    return rounds


def find_all_valid_distributions(total_games, d_opp, s_opp, i_opp, is_balanced=False):
    """Finds all valid game breakdown configurations, allowing for MLB's odd/split series."""
    valid_sols = []

    # FIX 1: Change the step from 2 to 1 to allow odd game totals like 13 and 3
    for g_d in range(2, total_games + 1):
        for g_s in range(2 if s_opp > 0 else 0, total_games + 1):
            
            if is_balanced and s_opp > 0 and g_d != g_s:
                continue
                
            used = d_opp * g_d + s_opp * g_s
            rem = total_games - used
            
            if rem < 0:
                continue

            if i_opp > 0:
                # Prevent zero-game interleague distributions if interleague is enabled
                if rem == 0:
                    continue
                    
                g_i = rem // i_opp
                i_rem = rem % i_opp
                
                # Condition A: Perfect Math (Fictional setups)
                if i_rem == 0 and g_i > 0:
                    valid_sols.append({
                        "g_div": g_d, "div_total": d_opp * g_d,
                        "g_sub": g_s, "sub_total": s_opp * g_s, "sub_extra": 0,
                        "g_inter": g_i, "inter_total": i_opp * g_i, "inter_extra": 0,
                        "total_games": total_games,
                        "is_pure_3g": (g_d % 3 == 0 and g_s % 3 == 0 and g_i % 3 == 0)
                    })
                
                # Condition B: MLB Split Math (13 Div, 6/7 Sub, 3/4 Inter)
                elif g_d == 13 and g_s == 6 and g_i == 3 and i_rem == 5:
                    valid_sols.append({
                        "g_div": g_d, "div_total": d_opp * g_d,
                        "g_sub": f"{g_s}/{g_s+1}", "sub_total": s_opp * g_s + 4, "sub_extra": 4,
                        "g_inter": f"{g_i}/{g_i+1}", "inter_total": (i_opp * g_i) + 1, "inter_extra": 1,
                        "total_games": total_games,
                        "is_pure_3g": False
                    })
            else:
                if rem == 0:
                    valid_sols.append({
                        "g_div": g_d, "div_total": d_opp * g_d,
                        "g_sub": g_s, "sub_total": s_opp * g_s, "sub_extra": 0,
                        "g_inter": 0, "inter_total": 0, "inter_extra": 0,
                        "total_games": total_games,
                        "is_pure_3g": (g_d % 3 == 0 and g_s % 3 == 0)
                    })

    # Sort heavily divisional options to the top (descending)
    # We use 'sub_total' instead of 'g_sub' to safely avoid string comparison errors
    valid_sols.sort(key=lambda x: (x["g_div"], x["is_pure_3g"], x["sub_total"]), reverse=True)

    return valid_sols


def prompt_user_for_distribution(solutions, d_opp, s_opp, i_opp):
    """Displays formatted breakdown choices and prompts user selection."""
    print("\n" + "=" * 85)
    print(" AVAILABLE GAME DISTRIBUTION BREAKDOWNS (Exact 81H / 81A Balance)")
    print("=" * 85)
    print(f"{'Opt':<4} | {'Divisional':<23} | {'Subleague Non-Div':<23} | {'Interleague':<23}")
    print("-" * 85)

    for idx, sol in enumerate(solutions, start=1):
        div_series = decompose_games_to_series(sol['g_div'])
        sub_series = decompose_games_to_series(sol['g_sub']) if s_opp > 0 else []
        inter_series = decompose_games_to_series(sol['g_inter']) if i_opp > 0 else []

        div_str = f"{sol['g_div']}g ({sol['div_total']}g) [{len(div_series)} ser]"
        sub_str = f"{sol['g_sub']}g ({sol['sub_total']}g) [{len(sub_series)} ser]" if s_opp > 0 else "N/A"
        inter_str = f"{sol['g_inter']}g ({sol['inter_total']}g) [{len(inter_series)} ser]" if i_opp > 0 else "N/A"

        pure_tag = " *" if sol['is_pure_3g'] else ""
        print(f"{idx:<4} | {div_str:<23} | {sub_str:<23} | {inter_str:<23}{pure_tag}")

    print("=" * 85)
    print(" * Indicates pure 3-game series breakdown. Mixed length used where noted.")

    while True:
        try:
            choice = input(f"Select breakdown option [1-{len(solutions)}] (default 1): ").strip()
            if choice == "":
                return solutions[0]
            val = int(choice)
            if 1 <= val <= len(solutions):
                return solutions[val - 1]
            print(f"Please enter a number between 1 and {len(solutions)}.")
        except ValueError:
            print("Invalid input. Enter an option number.")


def build_dynamic_schedule(
    subleagues, divs_per_sl, teams_per_div, total_games, chosen_sol, interleague=True, end_divisional=3
):
    team_id = 1
    structure = {}
    for sl in range(1, subleagues + 1):
        structure[sl] = {}
        for div in range(1, divs_per_sl + 1):
            structure[sl][div] = []
            for _ in range(teams_per_div):
                structure[sl][div].append(team_id)
                team_id += 1

    total_teams = team_id - 1

    div_series_lengths = decompose_games_to_series(chosen_sol.get("g_div", 0))
    sub_series_lengths = decompose_games_to_series(chosen_sol.get("g_sub", 0))
    inter_series_lengths = decompose_games_to_series(chosen_sol.get("g_inter", 0))

    div_windows, sub_windows, inter_windows = [], [], []

    # 1. Base Divisional Windows
    if div_series_lengths:
        div_rounds_map = {
            (sl_id, div_id): generate_circle_rounds(div_teams)
            for sl_id, sl in structure.items()
            for div_id, div_teams in sl.items()
        }
        num_div_rounds = len(next(iter(div_rounds_map.values())))

        for cycle_idx, s_len in enumerate(div_series_lengths):
            swap = cycle_idx % 2 == 1
            for r_idx in range(num_div_rounds):
                window = []
                for (sl_id, div_id), rounds in div_rounds_map.items():
                    for t1, t2 in rounds[r_idx]:
                        window.append({
                            "home": t2 if swap else t1,
                            "away": t1 if swap else t2,
                            "length": s_len,
                        })
                div_windows.append(window)

    # 2. Base Subleague Windows
    if sub_series_lengths and divs_per_sl > 1:
        div_keys = list(structure[1].keys())
        div_pairs = [(div_keys[i], div_keys[j]) for i in range(len(div_keys)) for j in range(i + 1, len(div_keys))]

        for cycle_idx, s_len in enumerate(sub_series_lengths):
            swap = cycle_idx % 2 == 1
            for d1_k, d2_k in div_pairs:
                sample_bipartite = generate_bipartite_rounds(structure[1][d1_k], structure[1][d2_k])
                for r_idx in range(len(sample_bipartite)):
                    window = []
                    for sl in structure.values():
                        cr = generate_bipartite_rounds(sl[d1_k], sl[d2_k])
                        for t1, t2 in cr[r_idx]:
                            window.append({
                                "home": t2 if swap else t1,
                                "away": t1 if swap else t2,
                                "length": s_len,
                            })
                    sub_windows.append(window)

    # 3. Base Interleague Windows
    if inter_series_lengths and subleagues > 1:
        sl1_teams = [t for div in structure[1].values() for t in div]
        sl2_teams = [t for div in structure[2].values() for t in div]
        cross_rounds = generate_bipartite_rounds(sl1_teams, sl2_teams)

        for cycle_idx, s_len in enumerate(inter_series_lengths):
            swap = cycle_idx % 2 == 1
            for r_idx in range(len(cross_rounds)):
                window = []
                for t1, t2 in cross_rounds[r_idx]:
                    window.append({
                        "home": t2 if swap else t1,
                        "away": t1 if swap else t2,
                        "length": s_len,
                    })
                inter_windows.append(window)

    # =========================================================
    # INJECTION: Apply Asymmetrical Splitting (e.g., 7-Game/4-Game series)
    # =========================================================
    sub_extra = chosen_sol.get("sub_extra", 0)
    inter_extra = chosen_sol.get("inter_extra", 0)

    def distribute_extras(windows_list, required_extras, max_series_length=4):
        if required_extras <= 0 or not windows_list:
            return
        
        team_extras = {t: 0 for t in range(1, total_teams + 1)}
        upgraded_pairings = set()
        
        for window in windows_list:
            for series in window:
                h, a = series["home"], series["away"]
                pairing = tuple(sorted([h, a]))
                
                # If both teams still need to satisfy their asymmetrical "extra" opponent count
                if team_extras[h] < required_extras and team_extras[a] < required_extras:
                    if pairing not in upgraded_pairings and series["length"] < max_series_length:
                        series["length"] += 1
                        team_extras[h] += 1
                        team_extras[a] += 1
                        upgraded_pairings.add(pairing)

    distribute_extras(sub_windows, sub_extra)
    distribute_extras(inter_windows, inter_extra)

    # =========================================================
    # BALANCING: Global Gradient Descent Home/Away Equalizer
    # =========================================================
    all_series_lists = [div_windows, sub_windows, inter_windows]
    home_counts = {t: 0 for t in range(1, total_teams + 1)}
    
    # Pass 1: Count Initial Global Home Games
    for lst in all_series_lists:
        for window in lst:
            for series in window:
                home_counts[series["home"]] += series["length"]

    target_home = total_games // 2
    improved = True
    passes = 0
    
    # Pass 2: Iteratively flip series to seek the 81-game H/A target for all teams
    while improved and passes < 20:
        improved = False
        passes += 1
        for lst in all_series_lists:
            for window in lst:
                for series in window:
                    h, a, length = series["home"], series["away"], series["length"]
                    
                    err_before = abs(home_counts[h] - target_home) + abs(home_counts[a] - target_home)
                    err_after = abs(home_counts[h] - length - target_home) + abs(home_counts[a] + length - target_home)
                    
                    # If flipping Home/Away reduces the total balance error, make the swap!
                    if err_after < err_before:
                        series["home"], series["away"] = a, h
                        home_counts[h] -= length
                        home_counts[a] += length
                        improved = True

    # =========================================================
    # REASSEMBLY: Final window compilation
    # =========================================================
    reserved_div_windows = []
    if divs_per_sl > 1 and end_divisional > 0 and len(div_windows) > end_divisional:
        reserved_div_windows = div_windows[-end_divisional:]
        div_windows = div_windows[:-end_divisional]

    windows = []
    max_len = max(len(lst) for lst in all_series_lists) if any(all_series_lists) else 0

    for idx in range(max_len):
        for lst in all_series_lists:
            if idx < len(lst):
                windows.append(lst[idx])

    windows.extend(reserved_div_windows)

    return windows, total_teams


def expand_to_slotted_games(windows, target_asg_day=0, asg_before=2, asg_after=1, asg_weekday_num=None, start_dow=2, max_consecutive_days=20, end_divisional=3):
    slotted_games = []
    
    # 1. Determine total teams
    teams = set()
    for w in windows:
        for s in w:
            teams.add(s["home"])
            teams.add(s["away"])
    total_teams = max(teams) if teams else 0

    if total_teams == 0:
        return [], 0

    team_busy_days = {t: set() for t in range(1, total_teams + 1)}
    
    def is_free(t, start, length):
        for d in range(start, start + length):
            if d in team_busy_days[t]: return False
        return True
        
    def current_streak(t, day):
        """Calculates how many consecutive days a team has played leading up to a given day."""
        c = 0
        d = day - 1
        while d in team_busy_days[t]:
            c += 1
            d -= 1
        return c

    # 2. Flatten windows into a total pool of available series
    reserved_start_idx = len(windows) - end_divisional if len(windows) > end_divisional else len(windows)
    normal_series = []
    reserved_series = []
    
    for w_idx, w in enumerate(windows):
        if w_idx >= reserved_start_idx:
            reserved_series.extend(w)
        else:
            normal_series.extend(w)
            
    # 3. Phase 1: Forward-March packing for normal series
    test_day = 1
    while normal_series:
        # Create a copy of the list so we can safely remove scheduled series during iteration
        for s in list(normal_series):
            h, a, length = s["home"], s["away"], s["length"]
            
            # Safety Valve: If the season is dragging past mid-September (Day 165+), 
            # relax the streak rules slightly to snap the final games into place.
            current_max_streak = max_consecutive_days + 5 if test_day > 165 else max_consecutive_days
            
            # If both teams are free and won't violate their exhaustion limit...
            if is_free(h, test_day, length) and is_free(a, test_day, length):
                if current_streak(h, test_day) + length <= current_max_streak and \
                   current_streak(a, test_day) + length <= current_max_streak:
                    
                    # Book the series!
                    for d in range(test_day, test_day + length):
                        team_busy_days[h].add(d)
                        team_busy_days[a].add(d)
                        slotted_games.append({
                            "day": d,
                            "time": "1905" if d < test_day + length - 1 else "1305",
                            "home": h,
                            "away": a,
                            "series_start": test_day,
                            "series_length": length
                        })
                    normal_series.remove(s)
                    
        # Advance the master calendar clock by 1 day
        test_day += 1

    # 4. Phase 2: Pack reserved divisional series strictly at the end
    global_max_day = max([d for days in team_busy_days.values() for d in days] + [0])
    test_day = global_max_day + 1
    
    while reserved_series:
        for s in list(reserved_series):
            h, a, length = s["home"], s["away"], s["length"]
            if is_free(h, test_day, length) and is_free(a, test_day, length):
                # No streak limits applied here to guarantee the season ends in unison
                for d in range(test_day, test_day + length):
                    team_busy_days[h].add(d)
                    team_busy_days[a].add(d)
                    slotted_games.append({
                        "day": d,
                        "time": "1905" if d < test_day + length - 1 else "1305",
                        "home": h,
                        "away": a,
                        "series_start": test_day,
                        "series_length": length
                    })
                reserved_series.remove(s)
        test_day += 1

    # 5. Phase 3: Inject the All-Star Break cleanly across the global schedule
    final_max_day = max([d for days in team_busy_days.values() for d in days] + [0])
    final_asg_day = 0
    
    # We maintain your original custom ASG inputs[cite: 1].
    if target_asg_day > 0 or asg_weekday_num is not None:
        if target_asg_day == 0:
            target_asg_day = final_max_day // 2
            
        final_asg_day = target_asg_day
        if asg_weekday_num is not None:
            diff = asg_weekday_num - get_weekday(target_asg_day, start_dow)
            if diff > 3: diff -= 7
            elif diff < -3: diff += 7
            final_asg_day += diff
            
        break_start = final_asg_day - asg_before
        break_end = final_asg_day + asg_after
        break_length = (break_end - break_start) + 1
        
        shifted = False
        min_shifted_start = float('inf')
        
        for g in slotted_games:
            series_end = g["series_start"] + g["series_length"] - 1
            if series_end >= break_start:
                if g["series_start"] < min_shifted_start:
                    min_shifted_start = g["series_start"]
                g["day"] += break_length
                shifted = True
                
        if shifted:
            final_asg_day = min_shifted_start + asg_before
            
    # Cleanup utility keys
    for g in slotted_games:
        g.pop("series_start", None)
        g.pop("series_length", None)
        
    return sorted(slotted_games, key=lambda x: (x["day"], x["home"])), final_asg_day


def main():
    parser = argparse.ArgumentParser(
        description="OOTP Schedule XML Generator supporting Mixed-Length Series & Interactive Options"
    )
    parser.add_argument("-s", "--subleagues", type=int, default=2)
    parser.add_argument("-d", "--divisions", type=int, default=2)
    parser.add_argument("-t", "--teams-per-div", type=int, default=4)
    parser.add_argument("-g", "--games", type=int, default=162)
    parser.add_argument("-il", "--interleague", type=int, choices=[0, 1], default=None)
    parser.add_argument("-bg", "--balanced", type=int, choices=[0, 1], default=0)
    parser.add_argument("-a", "--allstar-game-day", type=int, default=0, help="Target calendar day for the ASG")
    parser.add_argument("-aw", "--asg-weekday", type=str, default=None, help="Force ASG to fall on this day of the week (e.g., Thursday). Overrides -a.")
    parser.add_argument("-ab", "--asg-before", type=int, default=2)
    parser.add_argument("-aa", "--asg-after", type=int, default=1)
    parser.add_argument("-sdw", "--start-day-of-week", type=str, default="Monday")
    parser.add_argument("-sm", "--start-month", type=str, default="April")
    parser.add_argument("-sd", "--start-day", type=int, default=1)
    parser.add_argument("-o", "--output", type=str, default=None)
    parser.add_argument("--non-interactive", action="store_true", help="Auto-select top breakdown option")
    parser.add_argument("-ed", "--end-divisional", type=int, default=3, help="Number of divisional series reserved strictly for the end of the season")

    args = parser.parse_args()

    sdw_num = DAY_MAP.get(str(args.start_day_of_week).lower(), 2)
    sm_num = MONTH_MAP.get(str(args.start_month).lower(), 4)
    sd_num = args.start_day
    
    asg_weekday_num = DAY_MAP.get(str(args.asg_weekday).lower()) if args.asg_weekday else None

    il_flag = str(args.interleague) if args.interleague is not None else ("1" if args.subleagues > 1 else "0")
    bg_flag = str(args.balanced)
    
    il_str = "ILY" if il_flag == "1" else "ILN"
    bg_str = "BGY" if bg_flag == "1" else "BGN"
    
    il_prefix = f"{il_str}_{bg_str}"

    d_opp = args.teams_per_div - 1
    s_opp = (args.divisions - 1) * args.teams_per_div
    i_opp = (args.subleagues - 1) * args.divisions * args.teams_per_div if il_flag == "1" else 0

    is_balanced = (args.balanced == 1)
    solutions = find_all_valid_distributions(args.games, d_opp, s_opp, i_opp, is_balanced=is_balanced)

    if not solutions:
        print(f"Error: No valid game distributions found for {args.games} games.")
        sys.exit(1)

    if args.non_interactive or not sys.stdin.isatty():
        chosen_sol = solutions[0]
    else:
        chosen_sol = prompt_user_for_distribution(solutions, d_opp, s_opp, i_opp)

    sl_parts = [f"SL{sl}_" + "_".join([f"D{d}_T{args.teams_per_div}" for d in range(1, args.divisions + 1)]) for sl in range(1, args.subleagues + 1)]
    type_attr = f"{il_prefix}_G{args.games}_" + "_".join(sl_parts)
    filename = args.output if args.output else f"{type_attr}.lsdl"

    windows, total_teams = build_dynamic_schedule(
        args.subleagues, args.divisions, args.teams_per_div, args.games, chosen_sol, 
        interleague=(il_flag == "1"), 
        end_divisional=args.end_divisional
    )
    
    slotted_games, final_asg_day = expand_to_slotted_games(
        windows, 
        target_asg_day=args.allstar_game_day, 
        asg_before=args.asg_before, 
        asg_after=args.asg_after,
        asg_weekday_num=asg_weekday_num,
        start_dow=sdw_num,
        end_divisional=args.end_divisional
    )

    root_attrs = {
        "type": type_attr,
        "inter_league": il_flag,
        "balanced_games": bg_flag,
        "games_per_team": str(args.games),
        "start_day_of_week": str(sdw_num),
        "start_month": str(sm_num),
        "start_day": str(sd_num),
    }

    if final_asg_day > 0:
        root_attrs["allstar_game_day"] = str(final_asg_day)

    root = ET.Element("SCHEDULE", **root_attrs)
    games_element = ET.SubElement(root, "GAMES")

    for g in slotted_games:
        ET.SubElement(games_element, "GAME", day=str(g["day"]), time=str(g["time"]), away=str(g["away"]), home=str(g["home"]))

    xmlstr = minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")
    with open(filename, "w") as f:
        f.write(xmlstr)

    print(f"\nGenerated {len(slotted_games)} total games across {total_teams} teams.")
    if final_asg_day > 0:
        reverse_day_map = {1: "Sunday", 2: "Monday", 3: "Tuesday", 4: "Wednesday", 5: "Thursday", 6: "Friday", 7: "Saturday"}
        actual_dw = reverse_day_map[get_weekday(final_asg_day, sdw_num)]
        print(f"All-Star Game scheduled dynamically for Day {final_asg_day} ({actual_dw})")
    print(f"File saved to: {filename}")


if __name__ == "__main__":
    main()
