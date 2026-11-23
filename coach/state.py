from typing import TypedDict


class CoachState(TypedDict, total=False):
    match_id: str
    player_id: str
    pre_data: dict
    pre_analysis: str
    post_data: dict
    post_analysis: str
    takeaways: str
