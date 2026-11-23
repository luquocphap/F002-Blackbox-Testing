"""Level 1 unittest cases with test inputs and expected results loaded from CSV."""

import sys
from pathlib import Path

DIRECTORY = Path(__file__).resolve().parent
sys.path.insert(0, str(DIRECTORY.parent))

from automation import discover_cases, main

from level1.ui import UI

DATA = DIRECTORY / "test_data.csv"


def configuration():
    return UI


def load_tests(loader, _tests, _pattern):
    return discover_cases(loader, __name__, DATA, configuration)


if __name__ == "__main__":
    raise SystemExit(main(__name__, DATA, configuration))
