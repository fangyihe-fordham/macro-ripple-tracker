import json
from pathlib import Path
import pytest


@pytest.fixture
def fixtures_dir():
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def tmp_data_dir(tmp_path, monkeypatch):
    """Isolated data/ dir per test; modules read DATA_DIR env if set."""
    d = tmp_path / "data"
    d.mkdir()
    monkeypatch.setenv("DATA_DIR", str(d))
    return d
