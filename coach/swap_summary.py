ROLE_ORDER = ["vanguard", "duelist", "support"]
BRIEF_PLAY_MINUTES = 1.0
SWAP_NOTES = [
    "Order is the order each hero was first picked, not a timeline. Going back to a hero merges into its first entry, and there is no timing.",
    "brief = played under 1 minute; there are no stats for it.",
    "teamSplitWhileOnHero assumes teammates stayed on their first-pick roles. winRate is the season win rate of that split against the enemy split.",
]


def hero_pool_by_id(pick_alternatives: dict) -> dict[str, dict]:
    current_pick = pick_alternatives["currentPick"]
    pool = {current_pick["heroId"]: {"role": current_pick["role"], "teamSplit": current_pick.get("teamSplit")}}
    for alternative in pick_alternatives["alternatives"]:
        pool[alternative["heroId"]] = {
            "role": alternative["role"],
            "teamSplit": alternative.get("teamSplitIfSwapped"),
        }
    return pool


def split_with_target_on(role: str, teammate_roles: list[str]) -> str:
    all_roles = teammate_roles + [role]
    role_counts = []
    for role_name in ROLE_ORDER:
        role_counts.append(str(all_roles.count(role_name)))
    return "-".join(role_counts)


def build_swap_summary(match_context: dict, pick_alternatives: dict, hero_roles: dict[str, str]) -> dict:
    hero_pool = hero_pool_by_id(pick_alternatives)
    enemy_split = match_context["enemyTeam"]["split"]
    teammate_roles = []

    for player in match_context["myTeam"]["players"]:
        if not player["isTargetPlayer"]:
            teammate_roles.append(player["role"])

    result = match_context["result"]
    hero_rows = []
    
    for hero_played in result["heroesPlayed"]:
        hero_id = hero_played["heroId"]
        if hero_id is None:
            continue
        pool_entry = hero_pool.get(hero_id, {})
        role = pool_entry.get("role") or hero_roles.get(hero_id, "unknown")
        hero_row = {"heroId": hero_id, "role": role, "playMin": hero_played["playMin"]}

        if hero_played["playMin"] < BRIEF_PLAY_MINUTES:
            hero_row["brief"] = True
        else:
            hero_row["teamSplitWhileOnHero"] = pool_entry.get("teamSplit") or {
                "split": split_with_target_on(role, teammate_roles),
                "vsEnemySplit": enemy_split,
                "winRate": None,
            }
        hero_rows.append(hero_row)

    starting_role = hero_rows[0]["role"]
    for hero_row in hero_rows:
        hero_row["changedRoleFromStart"] = hero_row["role"] != starting_role

    final_hero_id = result["finalHeroId"]
    last_hero_id = hero_rows[-1]["heroId"]
    return {
        "startedOn": hero_rows[0]["heroId"],
        "finishedOn": final_hero_id,
        "wentBackToAnEarlierHero": final_hero_id != last_hero_id,
        "heroesInFirstSwapOrder": hero_rows,
        "notes": SWAP_NOTES,
    }
