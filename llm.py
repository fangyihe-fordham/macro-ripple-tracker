"""Central LLM client factory. All agents get their chat model from here."""
import os
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic

# override=True because Claude Desktop may export an empty ANTHROPIC_API_KEY
# in the parent shell; we want the real value from .env to win for live runs.
load_dotenv(override=True)

MODEL_ID = "claude-sonnet-4-6"
DEFAULT_TEMPERATURE = 0.2
DEFAULT_MAX_TOKENS = 4096


def get_chat_model(temperature: float = DEFAULT_TEMPERATURE,
                   max_tokens: int = DEFAULT_MAX_TOKENS) -> ChatAnthropic:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError(
            "ANTHROPIC_API_KEY not set. Copy .env.example to .env and paste your key."
        )
    return ChatAnthropic(
        model=MODEL_ID,
        temperature=temperature,
        max_tokens=max_tokens,
    )
