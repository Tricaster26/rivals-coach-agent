from typing import Literal

import httpx

Endpoint = Literal["match-context", "pick-alternatives", "match-performance", "eligibility"]
Phase = Literal["pre", "post"]


class AnalysisApiError(Exception):
    pass


class AnalysisApiClient:
    def __init__(self, base_url: str, api_key: str):
        self.http = httpx.Client(base_url=base_url, headers={"x-api-key": api_key}, timeout=60)

    def get(self, endpoint: Endpoint, match_id: str, player_id: str, phase: Phase | None = None) -> dict:
        params = {"matchId": match_id, "playerId": player_id}
        if phase is not None:
            params["phase"] = phase

        try:
            response = self.http.get(f"/analysis/{endpoint}", params=params)
        except httpx.ConnectError as error:
            raise AnalysisApiError(f"Can't reach the backend at {self.http.base_url}. Is it running?") from error

        if response.is_error:
            raise AnalysisApiError(f"/analysis/{endpoint} returned {response.status_code}: {response.text}")
        return response.json()
