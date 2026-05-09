"""Pytest config: ensure the lcp/ package is importable from this directory."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
