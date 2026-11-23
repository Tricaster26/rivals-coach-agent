import argparse
import sys

from langchain_groq import ChatGroq

from coach.api_client import AnalysisApiClient
from coach.config import RUNS_DIR, load_settings
from coach.game_data import NameResolver
from coach.graph import build_graph
from coach.nodes import CoachNodes
from coach.run_log import RunLog
from coach.state import CoachState

TEST_MATCH_ID = "5026135_1792074134_1231047_11001_22"
TEST_PLAYER_ID = "1148577256"
MAX_OUTPUT_TOKENS = 4000
MAX_RETRIES = 6


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Coach one player on one ranked match.")
    parser.add_argument("--match", default=TEST_MATCH_ID)
    parser.add_argument("--player", default=TEST_PLAYER_ID)
    parser.add_argument("--reasoning", choices=["low", "medium", "high"], default="medium")
    return parser.parse_args()


def build_report(final_state: CoachState) -> str:
    match_context = final_state["post_data"]["matchContext"]
    result = match_context["result"]
    score = result["score"]
    headline = (
        f"# {match_context['mapId']}: {result['result']} {score['myTeam']}-{score['enemyTeam']}, "
        f"elo {result['eloChange']:+}"
    )
    sections = [
        headline,
        "## Pre-match (what you could have known)",
        final_state["pre_analysis"],
        "## Post-match (what to reflect on)",
        final_state["post_analysis"],
        "## Takeaways",
        final_state["takeaways"],
    ]
    return "\n\n".join(sections) + "\n"


def print_usage(run_log: RunLog) -> None:
    total_tokens = 0
    for row in run_log.usage_rows:
        print(f"  {row['step']}: {row['inputTokens']} in + {row['outputTokens']} out")
        total_tokens += row["totalTokens"] or 0
    print(f"  total: {total_tokens} tokens")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args()
    settings = load_settings()

    llm = ChatGroq(
        model=settings.groq_model,
        api_key=settings.groq_api_key,
        reasoning_effort=args.reasoning,
        max_tokens=MAX_OUTPUT_TOKENS,
        max_retries=MAX_RETRIES,
    )
    run_log = RunLog(RUNS_DIR, args.match)
    nodes = CoachNodes(
        api_client=AnalysisApiClient(settings.analysis_api_url, settings.analysis_api_key),
        llm=llm,
        name_resolver=NameResolver(settings.game_data_dir),
        run_log=run_log,
    )

    print(f"Coaching match {args.match} for player {args.player} with {settings.groq_model}")
    final_state = build_graph(nodes).invoke({"match_id": args.match, "player_id": args.player})

    report = build_report(final_state)
    run_log.save_text("report.md", report)
    print()
    print(report)
    print("Token usage:")
    print_usage(run_log)
    print(f"Run saved to {run_log.folder}")


if __name__ == "__main__":
    main()
