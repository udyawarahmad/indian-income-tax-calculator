import os
import tempfile
from pathlib import Path

import pytest

# Set isolated data dir before importing app modules that read config at import time
_tmp = tempfile.mkdtemp(prefix="taxcalc_test_")
os.environ["TAX_CALC_DATA_DIR"] = _tmp

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def data_dir():
    return Path(_tmp)
