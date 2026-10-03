"""
Convenience entrypoint to execute the complete Sell Smart ML pipeline from the project root.
"""
import subprocess
import sys
from pathlib import Path

script_path = Path(__file__).parent / "sell_smart" / "scripts" / "run_pipeline.py"

if __name__ == "__main__":
    result = subprocess.run([sys.executable, str(script_path)])
    sys.exit(result.returncode)
