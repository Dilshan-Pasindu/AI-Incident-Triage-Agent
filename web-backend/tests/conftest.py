# web-backend/tests/conftest.py
import sys
from pathlib import Path

# Ensure web-backend directory is in sys.path so `import app` resolves
web_dir = Path(__file__).resolve().parent.parent
if str(web_dir) not in sys.path:
    sys.path.insert(0, str(web_dir))
