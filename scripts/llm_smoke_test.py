#!/usr/bin/env python3
"""
scripts/llm_smoke_test.py

Universal LLM API smoke test entrypoint.
Calls test_grok_smoke() from scripts/grok_smoke_test.py.
"""

import sys
from pathlib import Path

# Ensure script dir is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from grok_smoke_test import test_grok_smoke  # noqa: E402

if __name__ == "__main__":
    test_grok_smoke()
