"""
tests/test_tools.py
-------------------
Unit tests for utility functions in tools.py.
"""

import sys, os
import pytest
from pathlib import Path

# Ajout du dossier parent au PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from tools import list_input_files, save_report, annotated_path, ensure_dir
from config import INPUT_DIR, REPORTS_DIR, ANNOTATED_DIR


def test_input_dir_exists():
    """The input directory should exist and be accessible."""
    assert INPUT_DIR.exists(), f"Input directory missing: {INPUT_DIR}"


def test_list_input_files():
    """Listing input files should return a list (possibly empty)."""
    files = list_input_files()
    assert isinstance(files, list)
    for f in files:
        assert Path(f).exists()


def test_save_report(tmp_path):
    """Reports should be correctly saved as text files."""
    report_path = tmp_path / "sample_report.txt"
    save_report("example.txt", "This is a test report", base_dir=tmp_path)
    assert report_path.exists() or any(tmp_path.glob("*.txt"))


def test_annotated_path():
    """Annotated images should follow the correct naming pattern."""
    name = "mammogram_001.jpg"
    output = annotated_path(name)
    assert output.name.startswith("annotated_")
    assert output.suffix in [".jpg", ".png"]


def test_output_directories_exist():
    """All output directories should exist."""
    for d in [REPORTS_DIR, ANNOTATED_DIR]:
        ensure_dir(d)
        assert d.exists(), f"Directory missing: {d}"
