from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_groq import ChatGroq

from coach import prompts
from coach.api_client import AnalysisApiClient
from coach.game_data import NameResolver
from coach.highlight_candidates import build_highlight_candidates
from coach.review_rules import apply_review_rules
from coach.run_log import RunLog
from coach.state import CoachState
from coach.swap_summary import build_swap_summary
from coach.trim import (
    drop_alternatives_without_switch,
    drop_empty_bans,
    drop_matchup_lists_for_unplayed_heroes,
    drop_unused_fields,
    slim_post_match_context,
)


class CoachNodes:
    def __init__(self, api_client: AnalysisApiClient, llm: ChatGroq, name_resolver: NameResolver, run_log: RunLog):
        self.api_client = api_client
        self.llm = llm
        self.name_resolver = name_resolver
        self.run_log = run_log

    def fetch_pre(self, state: CoachState) -> CoachState:
        match_id = state["match_id"]
        player_id = state["player_id"]
        match_context = self.api_client.get("match-context", match_id, player_id, "pre")
        drop_empty_bans(match_context)
        pick_alternatives = self.api_client.get("pick-alternatives", match_id, player_id, "pre")
        drop_alternatives_without_switch(pick_alternatives)
        raw_pre_data = {
            "matchContext": match_context,
            "pickAlternatives": pick_alternatives,
        }
        pre_data = drop_unused_fields(self.name_resolver.resolve(raw_pre_data))
        self.run_log.save_json("1-pre-data.json", pre_data)
        return {"pre_data": pre_data}

    def analyze_pre(self, state: CoachState) -> CoachState:
        user_message = prompts.pre_user_message(state["pre_data"])
        pre_analysis = self.ask("2-analyze-pre", prompts.PRE_SYSTEM_PROMPT, user_message)
        return {"pre_analysis": pre_analysis}

    def fetch_post(self, state: CoachState) -> CoachState:
        match_id = state["match_id"]
        player_id = state["player_id"]
        match_context = self.api_client.get("match-context", match_id, player_id, "post")
        pick_alternatives = self.api_client.get("pick-alternatives", match_id, player_id, "post")
        match_performance = self.api_client.get("match-performance", match_id, player_id)

        swap_summary = build_swap_summary(match_context, pick_alternatives, self.name_resolver.hero_roles)
        played_hero_ids = set()
        for hero_played in match_context["result"]["heroesPlayed"]:
            played_hero_ids.add(hero_played["heroId"])
        drop_matchup_lists_for_unplayed_heroes(pick_alternatives, played_hero_ids)

        raw_post_data = {
            "matchContext": slim_post_match_context(match_context),
            "swapSummary": swap_summary,
            "matchPerformance": apply_review_rules(match_performance, swap_summary),
            "pickAlternatives": pick_alternatives,
        }
        post_data = drop_unused_fields(self.name_resolver.resolve(raw_post_data))
        self.run_log.save_json("3-post-data.json", post_data)
        return {"post_data": post_data}

    def analyze_post(self, state: CoachState) -> CoachState:
        user_message = prompts.post_user_message(state["post_data"], state["pre_analysis"])
        post_analysis = self.ask("4-analyze-post", prompts.POST_SYSTEM_PROMPT, user_message)
        return {"post_analysis": post_analysis}

    def write_takeaways(self, state: CoachState) -> CoachState:
        highlight_candidates = build_highlight_candidates(state["post_data"])
        self.run_log.save_json("5-highlight-candidates.json", highlight_candidates)
        user_message = prompts.takeaways_user_message(
            state["pre_analysis"], state["post_analysis"], highlight_candidates
        )
        takeaways = self.ask("5-takeaways", prompts.TAKEAWAYS_SYSTEM_PROMPT, user_message)
        return {"takeaways": takeaways}

    def ask(self, step_name: str, system_prompt: str, user_message: str) -> str:
        print(f"  {step_name}...", flush=True)
        messages = [SystemMessage(system_prompt), HumanMessage(user_message)]
        response: AIMessage = self.llm.invoke(messages)
        self.run_log.save_llm_step(step_name, system_prompt, user_message, response)
        return str(response.content).strip()
