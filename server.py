import json
import math
import sys
import threading
import time
import traceback
from collections.abc import Iterator
from dataclasses import dataclass
from queue import Queue

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from coach.api_client import AnalysisApiError
from coach.config import RUNS_DIR, load_settings
from coach.report import find_saved_report
from coach.runner import CoachRunner

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8000
COOLDOWN_SECONDS = 60
BUSY_RETRY_SECONDS = 30
REASONING = "medium"
RUN_FINISHED = None
STREAM_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}


@dataclass(frozen=True)
class Refusal:
    message: str
    retry_after_seconds: int


class RunGate:
    def __init__(self):
        self.lock = threading.Lock()
        self.last_run_finished_at: float | None = None

    def try_start(self) -> Refusal | None:
        if not self.lock.acquire(blocking=False):
            return Refusal("The coach is busy with another report.", BUSY_RETRY_SECONDS)

        cooldown_left = self.cooldown_left_seconds()
        if cooldown_left > 0:
            self.lock.release()
            return Refusal("The coach just finished a report. Try again shortly.", cooldown_left)
        return None

    def cancel(self) -> None:
        self.lock.release()

    def finish(self) -> None:
        self.last_run_finished_at = time.monotonic()
        self.lock.release()

    def cooldown_left_seconds(self) -> int:
        if self.last_run_finished_at is None:
            return 0
        elapsed = time.monotonic() - self.last_run_finished_at
        return max(0, math.ceil(COOLDOWN_SECONDS - elapsed))


class CoachRequest(BaseModel):
    matchId: str
    playerId: str


settings = load_settings()
runner = CoachRunner(settings)
gate = RunGate()

app = FastAPI(title="Rivals Coach Agent")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


def sse_event(event_name: str, data: dict) -> str:
    return f"event: {event_name}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def error_message(error: Exception) -> str:
    if isinstance(error, AnalysisApiError):
        return str(error)
    return "The coach couldn't finish this report. Check the agent server's log."


def run_in_background(match_id: str, player_id: str, events: Queue) -> None:
    try:
        for event in runner.run(match_id, player_id, REASONING):
            if isinstance(event, dict):
                events.put(sse_event("report", {"cached": False, **event}))
            else:
                events.put(sse_event("step", {"step": event}))
    except Exception as error:
        traceback.print_exc()
        events.put(sse_event("error", {"message": error_message(error)}))
    finally:
        gate.finish()
        events.put(RUN_FINISHED)


def queued_events(events: Queue) -> Iterator[str]:
    while True:
        event = events.get()
        if event is RUN_FINISHED:
            return
        yield event


def saved_report_events(report: dict) -> Iterator[str]:
    yield sse_event("report", {"cached": True, **report})


@app.get("/coach/eligibility")
def eligibility(matchId: str, playerId: str):
    try:
        return runner.api_client.get("eligibility", matchId, playerId)
    except AnalysisApiError as error:
        return JSONResponse(status_code=502, content={"message": str(error)})


@app.post("/coach")
def coach(request: CoachRequest):
    saved_report = find_saved_report(RUNS_DIR, request.matchId, request.playerId)
    if saved_report is not None:
        return StreamingResponse(saved_report_events(saved_report), media_type="text/event-stream")

    refusal = gate.try_start()
    if refusal is not None:
        return JSONResponse(
            status_code=429,
            content={"message": refusal.message, "retryAfterSeconds": refusal.retry_after_seconds},
        )

    try:
        player_eligibility = runner.api_client.get("eligibility", request.matchId, request.playerId)
    except AnalysisApiError as error:
        gate.cancel()
        return JSONResponse(status_code=502, content={"message": str(error)})

    if not player_eligibility["eligible"]:
        gate.cancel()
        return JSONResponse(
            status_code=422,
            content={"message": "This player can't be coached.", "reasons": player_eligibility["reasons"]},
        )

    events: Queue = Queue()
    worker = threading.Thread(
        target=run_in_background,
        args=(request.matchId, request.playerId, events),
        daemon=True,
    )
    worker.start()
    return StreamingResponse(queued_events(events), media_type="text/event-stream", headers=STREAM_HEADERS)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    uvicorn.run(app, host=SERVER_HOST, port=SERVER_PORT)
