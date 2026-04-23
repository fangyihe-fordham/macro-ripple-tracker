import os
import pytest
from llm import get_chat_model, MODEL_ID


def test_model_id_is_sonnet_4_6():
    assert MODEL_ID == "claude-sonnet-4-6"


def test_get_chat_model_requires_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        get_chat_model()


def test_get_chat_model_returns_chat_anthropic(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    m = get_chat_model()
    assert m.__class__.__name__ == "ChatAnthropic"
    assert getattr(m, "model", None) == MODEL_ID or getattr(m, "model_name", None) == MODEL_ID
