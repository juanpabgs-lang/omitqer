import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from backend.app.db import init_db
from backend.app.seed import seed


@pytest.fixture(scope="session")
def conn(tmp_path_factory):
    db = tmp_path_factory.mktemp("db") / "test.db"
    # smaller world for tests
    c = seed(path=db, n_members=400, n_docs=80, n_claims=200)
    return c


@pytest.fixture
def empty_conn(tmp_path):
    import sqlite3

    p = tmp_path / "empty.db"
    c = sqlite3.connect(str(p))
    c.row_factory = sqlite3.Row
    init_db(c)
    return c
