def target_hero_name(match_context: dict) -> str | None:
    for player in match_context["myTeam"]["players"]:
        if player.get("isTargetPlayer"):
            return player["firstHeroId"]
    return None


def teamup_sentence(owner: str, partner: str, target_hero: str | None) -> str:
    if target_hero == owner:
        return f"your {owner} gets it, enabled by {partner}"
    if target_hero == partner:
        return f"your {partner} enables it for {owner}"
    return f"{partner} enables it for {owner}"


def describe_teamups(match_context: dict) -> None:
    target_hero = target_hero_name(match_context)
    described_teamups = []
    for teamup in match_context.get("teamupsAvailable", []):
        described_teamups.append(
            {
                "abilityName": teamup["abilityName"],
                "whoGetsIt": teamup_sentence(teamup["ownerHeroId"], teamup["partnerHeroId"], target_hero),
                "involvesTargetPlayer": teamup["involvesTargetPlayer"],
            }
        )
    match_context["teamupsAvailable"] = described_teamups
