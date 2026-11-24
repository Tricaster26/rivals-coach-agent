from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph

from coach.sources.api_client import AnalysisApiClient
from coach.config import RUNS_DIR, load_settings
from coach.sources.game_data import NameResolver
from coach.pipeline.graph import build_graph
from coach.pipeline.nodes import CoachNodes
from coach.output.run_log import RunLog
from coach.runner import create_llm

DEFAULT_REASONING = "medium"
STUDIO_RUN_LABEL = "studio"

settings = load_settings()
api_client = AnalysisApiClient(settings.analysis_api_url, settings.analysis_api_key)
name_resolver = NameResolver(settings.game_data_dir)


def make_graph(config: RunnableConfig) -> CompiledStateGraph:
    configurable = config.get("configurable", {})
    reasoning = configurable.get("reasoning", DEFAULT_REASONING)
    nodes = CoachNodes(
        api_client=api_client,
        llm=create_llm(settings, reasoning),
        name_resolver=name_resolver,
        run_log=RunLog(RUNS_DIR, STUDIO_RUN_LABEL),
    )
    return build_graph(nodes)
