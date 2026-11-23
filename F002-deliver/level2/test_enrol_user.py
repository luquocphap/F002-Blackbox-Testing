"""Level 2 entry point. Test data, URLs, and locators are loaded from CSV."""

import sys
from pathlib import Path

DIRECTORY = Path(__file__).resolve().parent
sys.path.insert(0, str(DIRECTORY.parent))

from automation import main

if __name__ == "__main__":
    raise SystemExit(main(DIRECTORY, config_from_file=DIRECTORY / "ui_config.csv"))
