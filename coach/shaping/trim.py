from typing import Any

UNUSED_KEYS = {"matchId", "before", "season", "playerId", "thisMatchRemoved", "matchupDataMissing", "hasSeasonStats"}


def drop_unused_fields(value: Any) -> Any:
    if isinstance(value, dict):
        kept_fields = {}
        for key, child_value in value.items():
            if key in UNUSED_KEYS or child_value is None:
                continue
            kept_fields[key] = drop_unused_fields(child_value)
        return kept_fields
    if isinstance(value, list):
        return [drop_unused_fields(item) for item in value]
    return value


EMPTY_BAN_ID = "0"


def drop_empty_bans(match_context: dict) -> None:
    real_bans = []
    for ban in match_context.get("bans", []):
        if ban != EMPTY_BAN_ID:
            real_bans.append(ban)
    match_context["bans"] = real_bans


def drop_alternatives_without_switch(pick_alternatives: dict) -> None:
    current_pick = pick_alternatives.get("currentPick") or {}
    if current_pick.get("switchWorthConsidering"):
        return
    current_pick.pop("reasons", None)
    pick_alternatives.pop("alternatives", None)


def slim_post_match_context(match_context: dict) -> dict:
    return {
        "mapId": match_context["mapId"],
        "mode": match_context["mode"],
        "targetPlayer": match_context["targetPlayer"],
        "myTeam": {"avgEloBefore": match_context["myTeam"]["avgEloBefore"], "split": match_context["myTeam"]["split"]},
        "enemyTeam": {
            "avgEloBefore": match_context["enemyTeam"]["avgEloBefore"],
            "split": match_context["enemyTeam"]["split"],
        },
        "result": match_context["result"],
    }


def drop_matchup_lists_for_unplayed_heroes(pick_alternatives: dict, played_hero_ids: set[str]) -> None:
    for alternative in pick_alternatives["alternatives"]:
        if alternative["heroId"] not in played_hero_ids:
            alternative.pop("vsEnemies", None)
