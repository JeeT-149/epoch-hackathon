"""
Convenience entrypoint to run sell_smart/scripts/generate_all_synthetic_data.py
from the project root directory.
"""
import subprocess
import sys
from pathlib import Path

script_path = Path(__file__).parent / "sell_smart" / "scripts" / "generate_all_synthetic_data.py"

if __name__ == "__main__":
    result = subprocess.run([sys.executable, str(script_path)])
    sys.exit(result.returncode)
