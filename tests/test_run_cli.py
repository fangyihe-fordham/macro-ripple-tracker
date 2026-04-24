"""CLI smoke tests for run.py — verifies graceful error exits on bad input
without hitting the Anthropic API."""
import json
from datetime import date

import pytest

import agent_supervisor
import run as run_cli
from config import load_event


def test_cli_happy_path_prints_result_and_returns_zero(monkeypatch, capsys):
    fake_result = {"intent": "qa", "focus": "",
                   "response": {"answer": "ok", "citations": []}}
    monkeypatch.setattr(agent_supervisor, "run",
                        lambda cfg, query, as_of: fake_result)
    rc = run_cli.main(["--event", "iran_war", "--query", "what happened?"])
    assert rc == 0
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert parsed["intent"] == "qa"
    assert parsed["response"]["answer"] == "ok"


def test_cli_unknown_event_exits_nonzero(capsys):
    rc = run_cli.main(["--event", "does_not_exist",
                       "--query", "what happened?"])
    assert rc != 0
    err = capsys.readouterr().err
    assert "does_not_exist" in err


def test_cli_malformed_asof_exits_nonzero(capsys):
    rc = run_cli.main(["--event", "iran_war",
                       "--query", "what happened?",
                       "--as-of", "not-a-date"])
    assert rc != 0
    err = capsys.readouterr().err
    assert "as-of" in err.lower() or "iso" in err.lower() or "date" in err.lower()
