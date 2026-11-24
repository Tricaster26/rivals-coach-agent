import time

import groq
from langchain_core.language_models import BaseChatModel

from coach.llm import prompts
from coach.llm.ask import ask, json_mode
from coach.llm.takeaways import TakeawaysFormatError, check_confidence, load_json_object
from coach.output.run_log import RunLog

REVIEW_STEP = "6-review"
REVIEW_PAUSE_SECONDS = 60


def review_claims(reviewer_llm: BaseChatModel, run_log: RunLog, highlight_candidates: dict, claims: list[dict]) -> dict:
    reviews_by_id = {}
    for position, claim in enumerate(claims):
        if position > 0:
            time.sleep(REVIEW_PAUSE_SECONDS)
        reviews_by_id[claim["id"]] = review_one_claim(reviewer_llm, run_log, highlight_candidates, claim)
    run_log.save_json("6-claim-reviews.json", reviews_by_id)
    return reviews_by_id


def review_one_claim(reviewer_llm: BaseChatModel, run_log: RunLog, highlight_candidates: dict, claim: dict) -> dict:
    claim_to_review = {"id": claim["id"], "claim": claim["claim"], "basis": claim["basis"]}
    user_message = prompts.review_user_message(highlight_candidates, [claim_to_review])
    step_name = f"{REVIEW_STEP}-{claim['id']}"
    try:
        reply = ask(json_mode(reviewer_llm), run_log, step_name, prompts.REVIEW_SYSTEM_PROMPT, user_message)
        return parse_reviews(reply, [claim["id"]])[claim["id"]]
    except (TakeawaysFormatError, groq.APIError) as error:
        return {"reviewerConfidence": None, "reviewerReason": None, "reviewError": str(error)}


def parse_reviews(text: str, claim_ids: list[str]) -> dict:
    data = load_json_object(text, "reviews")
    review_list = data.get("reviews")
    if not isinstance(review_list, list):
        raise TakeawaysFormatError("reviews.reviews is not a list")

    reviews_by_id = {}
    for review in review_list:
        claim_id = review.get("id")
        if claim_id not in claim_ids:
            raise TakeawaysFormatError(f"review for unknown claim {claim_id!r}")
        reviewer_confidence = review.get("reviewerConfidence")
        reviewer_reason = review.get("reviewerReason")
        check_confidence(claim_id, "reviewerConfidence", reviewer_confidence)
        if not isinstance(reviewer_reason, str) or not reviewer_reason.strip():
            raise TakeawaysFormatError(f"review for {claim_id} has no reviewerReason")
        reviews_by_id[claim_id] = {
            "reviewerConfidence": reviewer_confidence,
            "reviewerReason": reviewer_reason.strip(),
        }

    missing_ids = [claim_id for claim_id in claim_ids if claim_id not in reviews_by_id]
    if missing_ids:
        raise TakeawaysFormatError(f"no review for {', '.join(missing_ids)}")
    return reviews_by_id
