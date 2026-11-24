import argparse
import sys

from coach.sources.api_client import AnalysisApiError
from coach.config import load_settings
from coach.output.report import report_markdown
from coach.output.run_log import RunLog
from coach.runner import CoachRunner

TEST_MATCH_ID = "5026135_1792074134_1231047_11001_22"
TEST_PLAYER_ID = "1148577256"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Coach one player on one ranked match.")
    parser.add_argument("--match", default=TEST_MATCH_ID)
    parser.add_argument("--player", default=TEST_PLAYER_ID)
    parser.add_argument("--reasoning", choices=["low", "medium", "high"], default="medium")
    return parser.parse_args()


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
    runner = CoachRunner(settings)

    print(f"Coaching match {args.match} for player {args.player} with {settings.groq_model}")
    report = None
    try:
        for event in runner.run(args.match, args.player, args.reasoning):
            if isinstance(event, dict):
                report = event
    except AnalysisApiError as error:
        raise SystemExit(str(error)) from error

    print()
    print(report_markdown(report))
    print("Token usage:")
    print_usage(runner.last_run_log)
    print(f"Run saved to {runner.last_run_log.folder}")


if __name__ == "__main__":
    main()
