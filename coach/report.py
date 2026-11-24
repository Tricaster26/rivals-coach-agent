import json
from pathlib import Path

from coach.state import CoachState

REPORT_FILE = "report.json"


def build_report(final_state: CoachState) -> dict:
    match_context = final_state["post_data"]["matchContext"]
    result = match_context["result"]
    return {
        "matchId": final_state["match_id"],
        "playerId": final_state["player_id"],
        "headline": {
            "map": match_context["mapId"],
            "result": result["result"],
            "score": result["score"],
            "eloChange": result["eloChange"],
        },
        "preMatch": final_state["pre_analysis"],
        "postMatch": final_state["post_analysis"],
        "takeaways": final_state["takeaways"],
        "takeawayClaims": final_state["takeaway_claims"],
    }


def report_markdown(report: dict) -> str:
    headline = report["headline"]
    score = headline["score"]
    title = (
        f"# {headline['map']}: {headline['result']} {score['myTeam']}-{score['enemyTeam']}, "
        f"elo {headline['eloChange']:+}"
    )
    sections = [
        title,
        "## Pre-match (what you could have known)",
        report["preMatch"],
        "## Post-match (what to reflect on)",
        report["postMatch"],
        "## Takeaways",
        report["takeaways"],
    ]
    return "\n\n".join(sections) + "\n"


def find_saved_report(runs_dir: Path, match_id: str, player_id: str) -> dict | None:
    run_folders = sorted(runs_dir.glob(f"*-{match_id}"), reverse=True)
    for run_folder in run_folders:
        report_path = run_folder / REPORT_FILE
        if not report_path.is_file():
            continue
        report = json.loads(report_path.read_text(encoding="utf-8"))
        if report.get("playerId") == player_id:
            return report
    return None
