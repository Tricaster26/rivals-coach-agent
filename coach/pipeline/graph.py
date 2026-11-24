from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from coach.pipeline.nodes import CoachNodes
from coach.pipeline.state import CoachState


def build_graph(nodes: CoachNodes) -> CompiledStateGraph:
    graph = StateGraph(CoachState)
    graph.add_node("fetch_pre", nodes.fetch_pre)
    graph.add_node("analyze_pre", nodes.analyze_pre)
    graph.add_node("fetch_post", nodes.fetch_post)
    graph.add_node("analyze_post", nodes.analyze_post)
    graph.add_node("write_takeaways", nodes.write_takeaways)

    graph.add_edge(START, "fetch_pre")
    graph.add_edge("fetch_pre", "analyze_pre")
    graph.add_edge("analyze_pre", "fetch_post")
    graph.add_edge("fetch_post", "analyze_post")
    graph.add_edge("analyze_post", "write_takeaways")
    graph.add_edge("write_takeaways", END)
    return graph.compile()
