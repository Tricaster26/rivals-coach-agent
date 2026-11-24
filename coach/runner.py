from collections.abc import Iterator
from typing import Literal

from langchain_groq import ChatGroq

from coach.sources.api_client import AnalysisApiClient
from coach.config import RUNS_DIR, Settings
from coach.sources.game_data import NameResolver
from coach.pipeline.graph import build_graph
from coach.pipeline.nodes import CoachNodes
from coach.output.report import REPORT_FILE, build_report, report_markdown
from coach.output.run_log import RunLog

Reasoning = Literal["low", "medium", "high"]
LlmStep = Literal["analyze_pre", "analyze_post", "write_takeaways"]

MAX_OUTPUT_TOKENS = 2500
REVIEWER_MAX_OUTPUT_TOKENS = 1000
MAX_RETRIES = 6

NEXT_LLM_STEP: dict[str, LlmStep] = {
    "fetch_pre": "analyze_pre",
    "fetch_post": "analyze_post",
    "analyze_post": "write_takeaways",
}


def create_llm(settings: Settings, reasoning: Reasoning) -> ChatGroq:
    return ChatGroq(
        model=settings.groq_model,
        api_key=settings.groq_api_key,
        reasoning_effort=reasoning,
        max_tokens=MAX_OUTPUT_TOKENS,
        max_retries=MAX_RETRIES,
    )


def create_reviewer_llm(settings: Settings, reasoning: Reasoning) -> ChatGroq:
    return ChatGroq(
        model=settings.reviewer_model,
        api_key=settings.groq_api_key,
        reasoning_effort=reasoning,
        reasoning_format="parsed",
        max_tokens=REVIEWER_MAX_OUTPUT_TOKENS,
        max_retries=MAX_RETRIES,
    )


class CoachRunner:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.api_client = AnalysisApiClient(settings.analysis_api_url, settings.analysis_api_key)
        self.name_resolver = NameResolver(settings.game_data_dir)
        self.last_run_log: RunLog | None = None

    def run(self, match_id: str, player_id: str, reasoning: Reasoning) -> Iterator[LlmStep | dict]:
        llm = create_llm(self.settings, reasoning)
        run_log = RunLog(RUNS_DIR, match_id)
        self.last_run_log = run_log
        nodes = CoachNodes(
            api_client=self.api_client,
            llm=llm,
            name_resolver=self.name_resolver,
            run_log=run_log,
        )
        graph = build_graph(nodes)

        final_state = {"match_id": match_id, "player_id": player_id}
        for update in graph.stream(final_state, stream_mode="updates"):
            for node_name, node_output in update.items():
                final_state.update(node_output)
                next_step = NEXT_LLM_STEP.get(node_name)
                if next_step is not None:
                    yield next_step

        report = build_report(final_state)
        run_log.save_json(REPORT_FILE, report)
        run_log.save_text("report.md", report_markdown(report))
        yield report
