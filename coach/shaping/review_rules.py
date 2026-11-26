AMOUNT_STATS = {"damage", "damageTaken", "healing"}
TRIVIAL_AMOUNT_PER_MIN = 100
ROLE_NEUTRAL_STATS = ["deaths", "kills", "finalHits"]
SECONDARY_STATS_BY_ROLE = {
    "vanguard": {"assists", "healing"},
    "duelist": {"assists", "healing"},
    "support": set(),
}
SECONDARY_WEIGHT = 0.5

HIGH_PERCENTILE = 75
LOW_PERCENTILE = 20
DEATHS_CONCERNING_PERCENTILE = 80
DEATHS_GOOD_PERCENTILE = 25
AVERAGE_BAND_LOW = 35
AVERAGE_BAND_HIGH = 60

DECIDES_RESULTS_REASON = "decides your results; outside your usual"
DECIDES_RESULTS_MIN_PRIORITY = 0.75

EXCEPTIONAL_TAIL_PERCENT = 15
VERY_TAIL_PERCENT = 35
EVEN_TEAM_SHARE = 0.17
SHARE_EXCEPTIONAL_DEVIATION = 0.75
SHARE_VERY_DEVIATION = 0.3


def strength_from_percentile(percentile: int | None) -> str | None:
    if percentile is None:
        return None
    tail_percent = min(percentile, 100 - percentile)
    if tail_percent <= EXCEPTIONAL_TAIL_PERCENT:
        return "exceptional"
    if tail_percent <= VERY_TAIL_PERCENT:
        return "very"
    return "mild"


def strength_from_share(share: float) -> str:
    deviation = abs(share - EVEN_TEAM_SHARE) / EVEN_TEAM_SHARE
    if deviation >= SHARE_EXCEPTIONAL_DEVIATION:
        return "exceptional"
    if deviation >= SHARE_VERY_DEVIATION:
        return "very"
    return "mild"


def is_trivial(stat_name: str, stat: dict) -> bool:
    if stat_name not in AMOUNT_STATS:
        return False
    recent_median = stat.get("recentMedianPerMin")
    return recent_median is not None and recent_median < TRIVIAL_AMOUNT_PER_MIN


def percentile_reason(stat_name: str, percentile: int | None) -> str | None:
    if percentile is None:
        return None
    if stat_name == "deaths":
        if percentile >= DEATHS_CONCERNING_PERCENTILE:
            return "concerning: many deaths for this hero"
        if percentile <= DEATHS_GOOD_PERCENTILE:
            return "good: few deaths for this hero"
        return None
    if percentile >= HIGH_PERCENTILE:
        return "high for this hero"
    if percentile <= LOW_PERCENTILE:
        return "low for this hero"
    return None


def decides_results_and_outside_usual(stat: dict) -> bool:
    separates = stat.get("separatesRecentWinsAndLosses") is True
    outside_usual = stat.get("vsRecentGames") in ("higher", "lower")
    return separates and outside_usual


def reasons_stat_is_notable(stat_name: str, stat: dict) -> list[str]:
    reasons = []
    reason_from_percentile = percentile_reason(stat_name, stat.get("higherThanPercentOfRankGames"))
    if reason_from_percentile is not None:
        reasons.append(reason_from_percentile)
    if decides_results_and_outside_usual(stat):
        reasons.append(DECIDES_RESULTS_REASON)
    return reasons


def compared_games_text(rank_tier: str | None) -> str:
    if rank_tier is None:
        return "games on this hero by players at your rank"
    return f"games on this hero by {rank_tier.capitalize()} players"


STAT_WORDS = {
    "damage": "damage",
    "damageTaken": "damage taken",
    "healing": "healing",
    "deaths": "deaths",
    "kills": "kills",
    "finalHits": "final hits",
    "assists": "assists",
    "soloKills": "solo kills",
}


def rank_standing(stat_name: str, percentile: int | None, rank_tier: str | None) -> str | None:
    if percentile is None:
        return None
    compared_games = compared_games_text(rank_tier)
    if AVERAGE_BAND_LOW <= percentile <= AVERAGE_BAND_HIGH:
        return f"around average for {compared_games}"
    stat_words = STAT_WORDS.get(stat_name, stat_name)
    if percentile > 50:
        return f"more {stat_words} than {percentile}% of {compared_games}"
    less_word = "less" if stat_name in AMOUNT_STATS else "fewer"
    return f"{less_word} {stat_words} than {100 - percentile}% of {compared_games}"


def per_min_text(value: float) -> str:
    if value == int(value):
        return f"{int(value)} per min"
    return f"{value} per min"


def wins_vs_losses(stat: dict) -> str | None:
    wins_median = stat.get("recentWinsMedianPerMin")
    losses_median = stat.get("recentLossesMedianPerMin")
    differs = stat.get("separatesRecentWinsAndLosses")
    if wins_median is None or losses_median is None or differs is None:
        return None

    wins_text = per_min_text(wins_median)
    losses_text = per_min_text(losses_median)
    if not differs:
        return f"no clear difference between your wins ({wins_text}) and losses ({losses_text})"

    direction = "higher" if wins_median > losses_median else "lower"
    sentence = f"{direction} in your wins ({wins_text}) than your losses ({losses_text})"
    resembles = stat.get("thisMatchResembles")
    if resembles == "recentWins":
        sentence += f"; this match ({per_min_text(stat['thisMatchPerMin'])}) looked like your wins"
    elif resembles == "recentLosses":
        sentence += f"; this match ({per_min_text(stat['thisMatchPerMin'])}) looked like your losses"
    return sentence


def priority_score(percentile: int | None, reasons: list[str], is_secondary: bool) -> float:
    score = 0.0
    if percentile is not None:
        score = abs(percentile - 50) / 50
    if DECIDES_RESULTS_REASON in reasons:
        score = max(score, DECIDES_RESULTS_MIN_PRIORITY)
    if is_secondary:
        score = score * SECONDARY_WEIGHT
    return round(score, 2)


def review_stat(stat_name: str, stat: dict, role: str, rank_tier: str | None) -> dict:
    percentile = stat.get("higherThanPercentOfRankGames")
    is_secondary = stat_name in SECONDARY_STATS_BY_ROLE.get(role, set())
    reasons = reasons_stat_is_notable(stat_name, stat)

    reviewed = {"priorityScore": priority_score(percentile, reasons, is_secondary)}
    if is_secondary:
        reviewed["secondary"] = True
    if reasons:
        reviewed["reasons"] = reasons
    reviewed["thisMatchTotal"] = stat["thisMatchTotal"]
    reviewed["thisMatchPerMin"] = stat["thisMatchPerMin"]
    reviewed["recentMedianPerMin"] = stat.get("recentMedianPerMin")
    reviewed["vsRecentGames"] = stat.get("vsRecentGames")
    reviewed["recentWinsMedianPerMin"] = stat.get("recentWinsMedianPerMin")
    reviewed["recentLossesMedianPerMin"] = stat.get("recentLossesMedianPerMin")
    reviewed["rankStanding"] = rank_standing(stat_name, percentile, rank_tier)
    reviewed["strength"] = strength_from_percentile(percentile)
    reviewed["differsInYourWinsAndLosses"] = stat.get("separatesRecentWinsAndLosses")
    reviewed["thisMatchResembles"] = stat.get("thisMatchResembles")
    wins_vs_losses_sentence = wins_vs_losses(stat)
    if wins_vs_losses_sentence is not None:
        reviewed["winsVsLosses"] = wins_vs_losses_sentence
    return reviewed


def priority_of(stat_entry: tuple[str, dict]) -> float:
    return stat_entry[1]["priorityScore"]


def review_hero(hero: dict, role: str) -> dict:
    reviewed_hero = {}
    for field_name, value in hero.items():
        if field_name != "stats":
            reviewed_hero[field_name] = value

    if hero.get("shortSample"):
        totals_only = {}
        for stat_name, stat in hero["stats"].items():
            totals_only[stat_name] = stat["thisMatchTotal"]
        reviewed_hero["totalsOnly"] = totals_only
        return reviewed_hero

    compared_with_rank = hero.get("comparedWithRank") or {}
    rank_tier = compared_with_rank.get("rankTier")
    reviewed_stats = {}
    for stat_name, stat in hero["stats"].items():
        if is_trivial(stat_name, stat):
            continue
        reviewed_stats[stat_name] = review_stat(stat_name, stat, role, rank_tier)

    stats_by_priority = sorted(reviewed_stats.items(), key=priority_of, reverse=True)
    reviewed_hero["stats"] = dict(stats_by_priority)
    return reviewed_hero


def review_team(team: dict, changed_role: bool) -> dict:
    reviewed_team = {}
    for stat_name, team_stat in team.items():
        kept_fields = dict(team_stat)
        if "gap" in kept_fields:
            kept_fields["teamGapAgainstEnemyTeam"] = kept_fields.pop("gap")
        if changed_role and stat_name not in ROLE_NEUTRAL_STATS:
            kept_fields.pop("targetPlayerShare", None)
        share = kept_fields.get("targetPlayerShare")
        if share is not None and stat_name in ROLE_NEUTRAL_STATS:
            kept_fields["targetPlayerShareStrength"] = strength_from_share(share)
        reviewed_team[stat_name] = kept_fields
    return reviewed_team


def apply_review_rules(match_performance: dict, swap_summary: dict) -> dict:
    role_by_hero = {}
    changed_role = False
    for swap_row in swap_summary["heroesInFirstSwapOrder"]:
        role_by_hero[swap_row["heroId"]] = swap_row["role"]
        if swap_row["changedRoleFromStart"]:
            changed_role = True

    reviewed_heroes = []
    for hero in match_performance["heroes"]:
        role = role_by_hero.get(hero["heroId"], "unknown")
        reviewed_heroes.append(review_hero(hero, role))

    reviewed_performance = dict(match_performance)
    reviewed_performance["heroes"] = reviewed_heroes
    reviewed_performance["team"] = review_team(match_performance["team"], changed_role)
    return reviewed_performance
