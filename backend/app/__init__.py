# The vision, controller (arm) and stockfish (engine) packages live in the
# project root, next to backend/. Make them importable for the server,
# alembic and pytest alike.
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
