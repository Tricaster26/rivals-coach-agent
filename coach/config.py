import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

AGENT_DIR = Path(__file__).resolve().parents[1]
RUNS_DIR = AGENT_DIR / "runs"
DEFAULT_FRONTEND_ORIGIN = "http://localhost:3000"

REQUIRED_VARIABLES = ["ANALYSIS_API_URL", "ANALYSIS_API_KEY", "GROQ_API_KEY", "GROQ_MODEL", "REVIEWER_MODEL", "GAME_DATA_DIR"]


@dataclass(frozen=True)
class Settings:
    analysis_api_url: str
    analysis_api_key: str
    groq_api_key: str
    groq_model: str
    reviewer_model: str
    game_data_dir: Path
    frontend_origin: str


def load_settings() -> Settings:
    load_dotenv(AGENT_DIR / ".env")
    missing_variables = [name for name in REQUIRED_VARIABLES if not os.getenv(name)]
    if missing_variables:
        raise SystemExit(f"Missing in rivals-coach-agent/.env: {', '.join(missing_variables)}")

    game_data_dir = (AGENT_DIR / os.environ["GAME_DATA_DIR"]).resolve()
    if not game_data_dir.is_dir():
        raise SystemExit(f"GAME_DATA_DIR does not exist: {game_data_dir}")

    return Settings(
        analysis_api_url=os.environ["ANALYSIS_API_URL"],
        analysis_api_key=os.environ["ANALYSIS_API_KEY"],
        groq_api_key=os.environ["GROQ_API_KEY"],
        groq_model=os.environ["GROQ_MODEL"],
        reviewer_model=os.environ["REVIEWER_MODEL"],
        game_data_dir=game_data_dir,
        frontend_origin=os.getenv("FRONTEND_ORIGIN", DEFAULT_FRONTEND_ORIGIN),
    )
