"""Superseded by install_fundradar_ui.py — kept so old shortcuts keep working."""
from pathlib import Path
import runpy
import sys

target = Path(__file__).resolve().parent / "install_fundradar_ui.py"
if not target.exists():
    print("ERROR: install_fundradar_ui.py is missing from the project folder.")
    raise SystemExit(1)

print("This script was replaced by install_fundradar_ui.py — running that.\n")
sys.argv = [str(target)]
runpy.run_path(str(target), run_name="__main__")
