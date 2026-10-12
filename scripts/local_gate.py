"""Portable local CI-equivalent core gate. Run on the exact candidate commit.

Usage: python scripts/local_gate.py
This does not assert hardware/GUI/OS cross-platform acceptance.
"""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
COMMANDS = [
    [sys.executable, "-m", "compileall", "-q", "pocket_manager"],
    [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
]

def main() -> int:
    for command in COMMANDS:
        print("$", " ".join(command), flush=True)
        result = subprocess.run(command, cwd=ROOT, check=False)
        if result.returncode:
            print(f"FAIL: exit code {result.returncode}", flush=True)
            return result.returncode
    print("PASS: syntax and unit tests (core only; no hardware/GUI smoke)", flush=True)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
