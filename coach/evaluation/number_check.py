import re

CLAIM_NUMBER = re.compile(r"\d[\d,  ]*(?:\.\d+)?")
DIGIT_SEPARATORS = [",", " ", " "]


def numbers_in_claim(claim_text: str) -> list[str]:
    numbers = []
    for match in CLAIM_NUMBER.finditer(claim_text):
        number_text = match.group().rstrip(",  ")
        for separator in DIGIT_SEPARATORS:
            number_text = number_text.replace(separator, "")
        numbers.append(number_text)
    return numbers


def numbers_in_data(value: object, found: set[float]) -> set[float]:
    if isinstance(value, bool):
        return found
    if isinstance(value, (int, float)):
        found.add(float(value))
        found.add(round(value * 100, 4))
    elif isinstance(value, str):
        for number_text in numbers_in_claim(value):
            found.add(float(number_text))
    elif isinstance(value, dict):
        for child in value.values():
            numbers_in_data(child, found)
    elif isinstance(value, list):
        for child in value:
            numbers_in_data(child, found)
    return found


def decimal_places(number_text: str) -> int:
    if "." not in number_text:
        return 0
    return len(number_text.split(".")[1])


def is_in_data(number_text: str, data_numbers: set[float]) -> bool:
    claim_number = float(number_text)
    places = decimal_places(number_text)
    for data_number in data_numbers:
        if round(data_number, places) == claim_number:
            return True
    return False


def numbers_not_in_data(claim_text: str, highlight_candidates: dict) -> list[str]:
    data_numbers = numbers_in_data(highlight_candidates, set())
    missing = []
    for number_text in numbers_in_claim(claim_text):
        if not is_in_data(number_text, data_numbers):
            missing.append(number_text)
    return missing
