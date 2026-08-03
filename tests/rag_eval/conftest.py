"""RAG evaluation fixtures."""
import json
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent


@pytest.fixture(scope="module")
def eval_queries():
    path = HERE / "queries.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def guidelines_dir():
    from pathlib import Path
    return Path(__file__).resolve().parent.parent.parent / "packages" / "haip-hospital" / "knowledge" / "guidelines"
