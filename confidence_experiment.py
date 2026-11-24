import argparse
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

from coach.config import AGENT_DIR, RUNS_DIR, load_settings
from coach.evaluation.number_check import numbers_not_in_data
from coach.evaluation.scoring import score_all_judges
from coach.llm.review import review_claims
from coach.llm.takeaways import all_claims, write_takeaway_claims
from coach.output.run_log import RunLog
from coach.runner import create_llm, create_reviewer_llm

EXPERIMENTS_DIR = AGENT_DIR / "experiments"
CLAIMS_FILE = "claims.json"
CLAIMS_VIEW_FILE = "claims.md"
MATCH_PAUSE_SECONDS = 60
REVIEW_FIELDS = ["reviewerConfidence", "reviewerReason", "reviewError"]
RUN_FOLDER = re.compile(r"^\d{8}-\d{6}-(?P<match_id>\d+_\d+_\d+_\d+_\d+)$")
REQUIRED_RUN_FILES = ["2-analyze-pre.output.md", "4-analyze-post.output.md", "5-highlight-candidates.json"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare the writer's and the reviewer's confidence on takeaway claims.")
    commands = parser.add_subparsers(dest="command", required=True)

    run_command = commands.add_parser("run", help="replay takeaways and reviews for saved runs")
    run_command.add_argument("--runs", nargs="*", help="folder names in runs/ (default: newest run of each match)")
    run_command.add_argument("--reasoning", choices=["low", "medium", "high"], default="medium")
    run_command.add_argument("--reviewer-reasoning", choices=["low", "medium", "high"], default="low")

    review_command = commands.add_parser("review", help="re-review an experiment's claims with the reviewer only")
    review_command.add_argument("--experiment", required=True, help="folder name in experiments/")
    review_command.add_argument("--reviewer-reasoning", choices=["low", "medium", "high"], default="low")
    review_command.add_argument("--claim-ids", nargs="*", help="only these claim ids, e.g. wentWell-3 (default: all)")

    score_command = commands.add_parser("score", help="score both models against your labels")
    score_command.add_argument("--experiment", required=True, help="folder name in experiments/")
    return parser.parse_args()


def has_required_files(run_folder: Path) -> bool:
    for file_name in REQUIRED_RUN_FILES:
        if not (run_folder / file_name).is_file():
            return False
    return True


def newest_run_per_match() -> list[Path]:
    newest_by_match: dict[str, Path] = {}
    for run_folder in sorted(RUNS_DIR.iterdir()):
        folder_match = RUN_FOLDER.match(run_folder.name)
        if folder_match is None or not has_required_files(run_folder):
            continue
        newest_by_match[folder_match.group("match_id")] = run_folder
    return list(newest_by_match.values())


def chosen_runs(run_names: list[str] | None) -> list[Path]:
    if not run_names:
        return newest_run_per_match()
    run_folders = []
    for run_name in run_names:
        run_folder = RUNS_DIR / run_name
        if not has_required_files(run_folder):
            raise SystemExit(f"{run_folder} is missing one of {', '.join(REQUIRED_RUN_FILES)}")
        run_folders.append(run_folder)
    return run_folders


def read_text(folder: Path, file_name: str) -> str:
    return (folder / file_name).read_text(encoding="utf-8").strip()


def match_id_of(run_folder: Path) -> str:
    folder_match = RUN_FOLDER.match(run_folder.name)
    return folder_match.group("match_id") if folder_match else run_folder.name


def claim_rows_for_run(run_folder: Path, experiment_folder: Path, llm, reviewer_llm) -> list[dict]:
    match_id = match_id_of(run_folder)
    highlight_candidates = json.loads(read_text(run_folder, "5-highlight-candidates.json"))
    run_log = RunLog(experiment_folder, match_id)

    claims_by_section = write_takeaway_claims(
        llm,
        run_log,
        read_text(run_folder, "2-analyze-pre.output.md"),
        read_text(run_folder, "4-analyze-post.output.md"),
        highlight_candidates,
    )
    claims = all_claims(claims_by_section)
    reviews = review_claims(reviewer_llm, run_log, highlight_candidates, claims)

    rows = []
    for claim in claims:
        review = reviews[claim["id"]]
        rows.append(
            {
                "matchId": match_id,
                "sourceRun": run_folder.name,
                **claim,
                **review,
                "precheck": {"numbersNotInData": numbers_not_in_data(claim["claim"], highlight_candidates)},
                "correct": None,
                "note": "",
            }
        )
    return rows


def claims_view(rows: list[dict]) -> str:
    lines = ["# Claims to label", "", f'Set "correct" to true or false for each claim in {CLAIMS_FILE}.', ""]
    for row in rows:
        lines.append(f"## {row['matchId']} / {row['id']}")
        lines.append("")
        lines.append(row["claim"])
        lines.append("")
        lines.append(f"- basis: {', '.join(row['basis'])}")
        lines.append(f"- gpt-oss: {row['modelConfidence']}, {row['confidenceReason']}")
        if row.get("reviewError"):
            lines.append(f"- qwen: no review ({row['reviewError']})")
        else:
            lines.append(f"- qwen: {row['reviewerConfidence']}, {row['reviewerReason']}")
        missing_numbers = row["precheck"]["numbersNotInData"]
        if missing_numbers:
            lines.append(f"- **numbers not found in the data: {', '.join(missing_numbers)}**")
        lines.append("")
    return "\n".join(lines)


def save_claims(experiment_folder: Path, rows: list[dict]) -> None:
    (experiment_folder / CLAIMS_FILE).write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    (experiment_folder / CLAIMS_VIEW_FILE).write_text(claims_view(rows), encoding="utf-8")


def run_experiment(args: argparse.Namespace) -> None:
    run_folders = chosen_runs(args.runs)
    settings = load_settings()
    llm = create_llm(settings, args.reasoning)
    reviewer_llm = create_reviewer_llm(settings, args.reviewer_reasoning)
    experiment_folder = EXPERIMENTS_DIR / datetime.now().strftime("%Y%m%d-%H%M%S")
    experiment_folder.mkdir(parents=True)
    print(f"Replaying {len(run_folders)} runs with {settings.groq_model} and {settings.reviewer_model}")

    rows: list[dict] = []
    for position, run_folder in enumerate(run_folders, start=1):
        if position > 1:
            time.sleep(MATCH_PAUSE_SECONDS)
        print(f"[{position}/{len(run_folders)}] {run_folder.name}")
        try:
            rows.extend(claim_rows_for_run(run_folder, experiment_folder, llm, reviewer_llm))
        except Exception as error:
            print(f"  skipped: {error}")
        save_claims(experiment_folder, rows)

    print(f"{len(rows)} claims saved to {experiment_folder / CLAIMS_FILE}")
    print(f"Label them, then run: python confidence_experiment.py score --experiment {experiment_folder.name}")


def rows_by_source_run(rows: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        grouped.setdefault(row["sourceRun"], []).append(row)
    return grouped


def review_experiment(args: argparse.Namespace) -> None:
    experiment_folder = EXPERIMENTS_DIR / args.experiment
    rows = json.loads((experiment_folder / CLAIMS_FILE).read_text(encoding="utf-8"))
    settings = load_settings()
    reviewer_llm = create_reviewer_llm(settings, args.reviewer_reasoning)
    rows_to_review = rows
    if args.claim_ids:
        rows_to_review = [row for row in rows if row["id"] in args.claim_ids]
    grouped_rows = rows_by_source_run(rows_to_review)
    print(f"Re-reviewing {len(rows_to_review)} claims from {len(grouped_rows)} runs with {settings.reviewer_model}")

    for position, (source_run, run_rows) in enumerate(grouped_rows.items(), start=1):
        if position > 1:
            time.sleep(MATCH_PAUSE_SECONDS)
        print(f"[{position}/{len(grouped_rows)}] {source_run}")
        highlight_candidates = json.loads(read_text(RUNS_DIR / source_run, "5-highlight-candidates.json"))
        run_log = RunLog(experiment_folder, f"{run_rows[0]['matchId']}-rereview")
        reviews = review_claims(reviewer_llm, run_log, highlight_candidates, run_rows)
        for row in run_rows:
            for field_name in REVIEW_FIELDS:
                row.pop(field_name, None)
            row.update(reviews[row["id"]])
        save_claims(experiment_folder, rows)
    print(f"Reviews saved to {experiment_folder / CLAIMS_FILE}")


def format_confidence(value: float | None) -> str:
    return "-" if value is None else f"{value:.0f}"


def score_experiment(args: argparse.Namespace) -> None:
    claims_path = EXPERIMENTS_DIR / args.experiment / CLAIMS_FILE
    rows = json.loads(claims_path.read_text(encoding="utf-8"))
    labelled_rows = [row for row in rows if isinstance(row.get("correct"), bool)]
    correct_count = sum(1 for row in labelled_rows if row["correct"])
    print(f"{len(labelled_rows)} of {len(rows)} claims labelled: {correct_count} correct, "
          f"{len(labelled_rows) - correct_count} wrong")
    print()
    print(f"{'judge':<18} {'claims':>6} {'avg if correct':>15} {'avg if wrong':>13} {'brier':>6}")
    for score in score_all_judges(labelled_rows):
        print(
            f"{score.judge:<18} {score.claims_scored:>6} {format_confidence(score.average_when_correct):>15} "
            f"{format_confidence(score.average_when_wrong):>13} {score.brier_score:>6.3f}"
        )
    print()
    print("Better judge: higher average when correct, lower when wrong, lower brier (0 is perfect, 0.25 is a coin flip).")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args()
    if args.command == "run":
        run_experiment(args)
    elif args.command == "review":
        review_experiment(args)
    else:
        score_experiment(args)


if __name__ == "__main__":
    main()
