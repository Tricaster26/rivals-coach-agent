ROLE_NEUTRAL_STATS = ["deaths", "kills", "finalHits"]
EVEN_TEAM_SHARE = 0.17


def priority_of(entry: dict) -> float:
    return entry["priorityScore"]


def play_minutes_of(hero: dict) -> float:
    return hero["playMin"]


def notable_stats_for(hero: dict) -> list[dict]:
    notable_stats = []
    for stat_name, stat in hero["stats"].items():
        if "reasons" not in stat:
            continue
        weighted_priority = stat["priorityScore"] * hero["shareOfMatch"]
        notable_stat = {"stat": stat_name, "weightedPriority": round(weighted_priority, 2)}
        notable_stat.update(stat)
        notable_stats.append(notable_stat)
    notable_stats.sort(key=priority_of, reverse=True)
    return notable_stats


def deviation_from_even_share(share: float) -> float:
    return min(abs(share - EVEN_TEAM_SHARE) / EVEN_TEAM_SHARE, 1.0)


def team_shares(team: dict) -> list[dict]:
    shares = []
    for stat_name in ROLE_NEUTRAL_STATS:
        share = team[stat_name].get("targetPlayerShare")
        if share is None:
            continue
        shares.append(
            {
                "stat": stat_name,
                "priorityScore": round(deviation_from_even_share(share), 2),
                "yourShareOfTeamTotal": share,
                "evenShare": EVEN_TEAM_SHARE,
                "teamTotal": team[stat_name]["myTeam"],
            }
        )
    shares.sort(key=priority_of, reverse=True)
    return shares


def build_highlight_candidates(post_data: dict) -> dict:
    swap_summary = post_data["swapSummary"]
    role_by_hero = {}
    for swap_row in swap_summary["heroesInFirstSwapOrder"]:
        role_by_hero[swap_row["heroId"]] = swap_row["role"]

    match_performance = post_data["matchPerformance"]
    heroes_by_play_time = sorted(match_performance["heroes"], key=play_minutes_of, reverse=True)

    hero_candidates = []
    short_sample_heroes = []
    for hero in heroes_by_play_time:
        if hero.get("shortSample"):
            short_sample_heroes.append({"hero": hero["heroId"], "playMin": hero["playMin"], "totals": hero["totalsOnly"]})
            continue
        hero_candidates.append(
            {
                "hero": hero["heroId"],
                "role": role_by_hero.get(hero["heroId"], "unknown"),
                "playMin": hero["playMin"],
                "shareOfMatch": hero["shareOfMatch"],
                "comparedWithRank": hero.get("comparedWithRank", {}).get("rankTier"),
                "recentRecordOnHero": hero["recentGames"]["record"],
                "notableStats": notable_stats_for(hero),
            }
        )

    return {
        "result": post_data["matchContext"]["result"]["result"],
        "heroesByPlayTime": hero_candidates,
        "shortSampleHeroes": short_sample_heroes,
        "teamShares": team_shares(match_performance["team"]),
        "swapSummary": swap_summary,
    }
