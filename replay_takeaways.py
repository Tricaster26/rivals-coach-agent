import argparse
import json
import sys
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage

from coach.llm import prompts
from coach.config import RUNS_DIR, load_settings
from coach.pipeline.nodes import JSON_RESPONSE_FORMAT
from coach.output.run_log import RunLog
from coach.runner import create_llm
from coach.llm.takeaways import parse_takeaway_claims, takeaways_markdown

REPLAY_SUFFIX = "takeaways-replay"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rerun only the takeaways step of a saved run with the current prompt.")
    parser.add_argument("--run", required=True, help="folder name inside runs/")
    parser.add_argument("--reasoning", choices=["low", "medium", "high"], default="medium")
    return parser.parse_args()


def read_text(folder: Path, file_name: str) -> str:
    return (folder / file_name).read_text(encoding="utf-8").strip()


def print_claims(claims_by_section: dict) -> None:
    for section_key, claims in claims_by_section.items():
        print(f"{section_key}:")
        for claim in claims:
            print(f"  [{claim['modelConfidence']}] {claim['claim']}")
            print(f"        basis: {', '.join(claim['basis'])}")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args()
    source_folder = RUNS_DIR / args.run
    if not source_folder.is_dir():
        raise SystemExit(f"No saved run at {source_folder}")

    pre_analysis = read_text(source_folder, "2-analyze-pre.output.md")
    post_analysis = read_text(source_folder, "4-analyze-post.output.md")
    highlight_candidates = json.loads(read_text(source_folder, "5-highlight-candidates.json"))
    user_message = prompts.takeaways_user_message(pre_analysis, post_analysis, highlight_candidates)

    settings = load_settings()
    llm = create_llm(settings, args.reasoning).bind(response_format=JSON_RESPONSE_FORMAT)
    run_log = RunLog(RUNS_DIR, f"{args.run}-{REPLAY_SUFFIX}")
    messages = [SystemMessage(prompts.TAKEAWAYS_SYSTEM_PROMPT), HumanMessage(user_message)]
    response = llm.invoke(messages)
    run_log.save_llm_step("5-takeaways", prompts.TAKEAWAYS_SYSTEM_PROMPT, user_message, response)

    claims_by_section = parse_takeaway_claims(str(response.content))
    run_log.save_json("takeaway-claims.json", claims_by_section)
    run_log.save_text("takeaways.md", takeaways_markdown(claims_by_section))

    print_claims(claims_by_section)
    print()
    print(takeaways_markdown(claims_by_section))
    usage = run_log.usage_rows[0]
    print(f"\nTokens: {usage['inputTokens']} in + {usage['outputTokens']} out")
    print(f"Saved to {run_log.folder}")


if __name__ == "__main__":
    main()
