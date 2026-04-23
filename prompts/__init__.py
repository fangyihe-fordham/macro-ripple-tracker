from pathlib import Path

_HERE = Path(__file__).parent


def load(name: str) -> str:
    """Load a prompt by filename (without .txt)."""
    return (_HERE / f"{name}.txt").read_text().strip()
