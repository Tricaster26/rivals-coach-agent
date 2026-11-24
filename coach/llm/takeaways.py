import json

from langchain_core.language_models import BaseChatModel

from coach.llm import prompts
from coach.llm.ask import ask, json_mode
from coach.output.run_log import RunLog

TAKEAWAYS_STEP = "5-takeaways"
MAX_CLAIMS_PER_SECTION = 3

SECTIONS = [
    ("wentWell", "What went well", "Nothing stood out."),
    ("concerning", "What stood out as concerning", "Nothing concerning stood out."),
]


class TakeawaysFormatError(ValueError):
    pass


def write_takeaway_claims(
    llm: BaseChatModel,
    run_log: RunLog,
    pre_analysis: str,
    post_analysis: str,
    highlight_candidates: dict,
) -> dict:
    user_message = prompts.takeaways_user_message(pre_analysis, post_analysis, highlight_candidates)
    reply = ask(json_mode(llm), run_log, TAKEAWAYS_STEP, prompts.TAKEAWAYS_SYSTEM_PROMPT, user_message)
    return parse_takeaway_claims(reply)


def parse_takeaway_claims(text: str) -> dict:
    data = load_json_object(text, "takeaways")
    claims_by_section = {}
    for section_key, _, _ in SECTIONS:
        claims = data.get(section_key)
        if not isinstance(claims, list):
            raise TakeawaysFormatError(f"takeaways.{section_key} is not a list")
        if len(claims) > MAX_CLAIMS_PER_SECTION:
            raise TakeawaysFormatError(f"takeaways.{section_key} has {len(claims)} claims")
        checked_claims = []
        for position, claim in enumerate(claims, start=1):
            claim_id = f"{section_key}-{position}"
            checked_claims.append(check_claim(claim_id, claim))
        claims_by_section[section_key] = checked_claims
    return claims_by_section


def load_json_object(text: str, label: str) -> dict:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as error:
        raise TakeawaysFormatError(f"{label} are not valid JSON: {error}") from error
    if not isinstance(data, dict):
        raise TakeawaysFormatError(f"{label} are not a JSON object")
    return data


def check_claim(claim_id: str, claim: dict) -> dict:
    text = claim.get("claim")
    model_confidence = claim.get("modelConfidence")
    confidence_reason = claim.get("confidenceReason")
    basis = claim.get("basis")
    if not isinstance(text, str) or not text.strip():
        raise TakeawaysFormatError(f"claim {claim_id} has no text")
    check_confidence(claim_id, "modelConfidence", model_confidence)
    if not isinstance(confidence_reason, str) or not confidence_reason.strip():
        raise TakeawaysFormatError(f"claim {claim_id} has no confidenceReason")
    if not isinstance(basis, list) or not all(isinstance(field, str) for field in basis):
        raise TakeawaysFormatError(f"claim {claim_id} has basis {basis!r}")
    return {
        "id": claim_id,
        "claim": text.strip(),
        "modelConfidence": model_confidence,
        "confidenceReason": confidence_reason.strip(),
        "basis": basis,
    }


def check_confidence(claim_id: str, field_name: str, value: object) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 100:
        raise TakeawaysFormatError(f"claim {claim_id} has {field_name} {value!r}")


def all_claims(claims_by_section: dict) -> list[dict]:
    claims = []
    for section_key, _, _ in SECTIONS:
        claims.extend(claims_by_section[section_key])
    return claims


def takeaways_markdown(claims_by_section: dict) -> str:
    lines = []
    for section_key, heading, empty_line in SECTIONS:
        if lines:
            lines.append("")
        lines.append(f"### {heading}")
        claims = claims_by_section[section_key]
        if not claims:
            lines.append(empty_line)
        for claim in claims:
            lines.append(f"- {claim['claim']}")
    return "\n".join(lines)
