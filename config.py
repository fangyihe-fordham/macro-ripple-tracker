from datetime import date
from pathlib import Path
from typing import List
import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, model_validator

# Load .env at import time so every entry point that touches config
# (setup.py, pytest, Streamlit app) sees NEWSAPI_KEY / ANTHROPIC_API_KEY.
load_dotenv()


class Ticker(BaseModel):
    category: str
    name: str
    symbol: str


class EventConfig(BaseModel):
    name: str
    display_name: str
    start_date: date
    end_date: date
    baseline_date: date
    seed_keywords: List[str]
    tickers: List[Ticker]
    rss_feeds: List[str] = []

    @model_validator(mode="after")
    def _check_dates(self):
        if self.baseline_date >= self.start_date:
            raise ValueError("baseline_date must be before start_date")
        if self.end_date < self.start_date:
            raise ValueError("end_date must be >= start_date")
        return self


def load_event(name: str, events_dir: Path | None = None) -> EventConfig:
    root = events_dir or Path("events")
    path = root / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Event config not found: {path}")
    with path.open() as f:
        raw = yaml.safe_load(f)
    return EventConfig(**raw)
