from dataclasses import dataclass

CONFIDENCE_FIELDS = [
    ("gpt-oss (writer)", "modelConfidence"),
    ("qwen (reviewer)", "reviewerConfidence"),
]


@dataclass(frozen=True)
class ConfidenceScore:
    judge: str
    claims_scored: int
    average_when_correct: float | None
    average_when_wrong: float | None
    brier_score: float


def average(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def score_judge(judge: str, confidence_field: str, labelled_claims: list[dict]) -> ConfidenceScore | None:
    when_correct = []
    when_wrong = []
    squared_errors = []
    for claim in labelled_claims:
        confidence = claim.get(confidence_field)
        if confidence is None:
            continue
        outcome = 1.0 if claim["correct"] else 0.0
        squared_errors.append((confidence / 100 - outcome) ** 2)
        if claim["correct"]:
            when_correct.append(confidence)
        else:
            when_wrong.append(confidence)
    if not squared_errors:
        return None
    return ConfidenceScore(
        judge=judge,
        claims_scored=len(squared_errors),
        average_when_correct=average(when_correct),
        average_when_wrong=average(when_wrong),
        brier_score=average(squared_errors),
    )


def score_all_judges(labelled_claims: list[dict]) -> list[ConfidenceScore]:
    scores = []
    for judge, confidence_field in CONFIDENCE_FIELDS:
        score = score_judge(judge, confidence_field, labelled_claims)
        if score is not None:
            scores.append(score)
    return scores
