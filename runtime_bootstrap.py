"""Load project-local packages without changing the user's Python environment."""
import os
import site
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
vendor = ROOT / 'vendor'
sys.path.insert(0, str(vendor))
site.addsitedir(str(vendor))
if os.name == 'nt' and (vendor / 'pywin32_system32').is_dir():
    _dll_directory = os.add_dll_directory(str(vendor / 'pywin32_system32'))
