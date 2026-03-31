#!/usr/bin/env python3
"""Thin runner for the refactored modular pipeline."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from joss_deco.cli import main


if __name__ == "__main__":
    main()
