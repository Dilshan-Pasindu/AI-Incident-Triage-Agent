# agent-client/conftest.py
# Root conftest: ensures the agent-client directory is on sys.path so that
# server.py and runs.py (not yet moved to web-backend) are importable by test_server.py.
import sys
from pathlib import Path

# agent-client/ itself must be on the path for the web-layer modules (server, runs)
_AC = Path(__file__).resolve().parent
if str(_AC) not in sys.path:
    sys.path.insert(0, str(_AC))
