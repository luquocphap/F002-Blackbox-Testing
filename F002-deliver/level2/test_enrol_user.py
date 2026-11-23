"""Level 2 unittest cases with test data, URLs, and locators loaded from CSV."""

import sys
from pathlib import Path

DIRECTORY = Path(__file__).resolve().parent
sys.path.insert(0, str(DIRECTORY.parent))

from automation import discover_cases, main, read_csv

DATA = DIRECTORY / "test_data.csv"


def configuration():
    return {row["name"]: (row["type"], row["value"]) for row in read_csv(DIRECTORY / "ui_config.csv")}


def load_tests(loader, _tests, _pattern):
    return discover_cases(loader, __name__, DATA, configuration)


if __name__ == "__main__":
    raise SystemExit(main(__name__, DATA, configuration))
