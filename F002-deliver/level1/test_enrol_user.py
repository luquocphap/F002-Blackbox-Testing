"""Level 1 entry point. Test inputs and expected results are loaded from CSV."""

import sys
from pathlib import Path

from ui import UI

DIRECTORY = Path(__file__).resolve().parent
sys.path.insert(0, str(DIRECTORY.parent))

from automation import main

if __name__ == "__main__":
    raise SystemExit(main(DIRECTORY, config=UI))
