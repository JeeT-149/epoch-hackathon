"""
conftest.py — top-level pytest configuration for sell_smart tests.
Adds src/ to sys.path so that 'sellsmart' can be imported without installation.
"""
import sys
from pathlib import Path

# Ensure sellsmart package is importable from tests
_src = Path(__file__).parent / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))
