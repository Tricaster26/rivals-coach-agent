import json

MAX_CLAIMS_PER_SECTION = 3

SECTIONS = [
    ("wentWell", "What went well", "Nothing stood out."),
    ("concerning", "What stood out as concerning", "Nothing concerning stood out."),
]


class TakeawaysFormatError(ValueError):
    pass


def parse_takeaway_claims(text: str) -> dict:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as error:
        raise TakeawaysFormatError(f"takeaways are not valid JSON: {error}") from error

    claims_by_section = {}
    for section_key, _, _ in SECTIONS:
        claims = data.get(section_key)
        if not isinstance(claims, list):
            raise TakeawaysFormatError(f"takeaways.{section_key} is not a list")
        if len(claims) > MAX_CLAIMS_PER_SECTION:
            raise TakeawaysFormatError(f"takeaways.{section_key} has {len(claims)} claims")
        claims_by_section[section_key] = [check_claim(section_key, claim) for claim in claims]
    return claims_by_section


def check_claim(section_key: str, claim: dict) -> dict:
    text = claim.get("claim")
    model_confidence = claim.get("modelConfidence")
    basis = claim.get("basis")
    if not isinstance(text, str) or not text.strip():
        raise TakeawaysFormatError(f"a {section_key} claim has no text")
    if not isinstance(model_confidence, int) or not 0 <= model_confidence <= 100:
        raise TakeawaysFormatError(f"a {section_key} claim has modelConfidence {model_confidence!r}")
    if not isinstance(basis, list) or not all(isinstance(field, str) for field in basis):
        raise TakeawaysFormatError(f"a {section_key} claim has basis {basis!r}")
    return {"claim": text.strip(), "modelConfidence": model_confidence, "basis": basis}


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
