"""Unit tests for report generation."""

import json
import tempfile
from pathlib import Path

import pytest

from src.report_generator import NoiseReport


class TestNoiseReport:
    def test_add_noise(self):
        report = NoiseReport(total_samples=100)
        report.add_noise("syntax_error", 5)
        report.add_noise("empty_method", 3)
        report.add_noise("syntax_error", 2)  # accumulate

        assert report.breakdown["syntax_error"] == 7
        assert report.breakdown["empty_method"] == 3
        assert report.removed_samples == 10

    def test_finalize(self):
        report = NoiseReport(total_samples=100)
        report.add_noise("syntax_error", 20)
        report.finalize()

        assert report.kept_samples == 80
        assert report.removal_rate == pytest.approx(0.2)

    def test_to_json(self):
        report = NoiseReport(total_samples=50)
        report.add_noise("no_relevance", 10)
        report.finalize()

        with tempfile.TemporaryDirectory() as tmpdir:
            path = report.to_json(Path(tmpdir) / "report.json")
            assert path.exists()

            with open(path) as f:
                data = json.load(f)
            assert data["total_samples"] == 50
            assert data["removed_samples"] == 10
            assert data["kept_samples"] == 40

    def test_to_markdown(self):
        report = NoiseReport(total_samples=50)
        report.add_noise("syntax_error", 5)
        report.add_noise("no_relevance", 10)
        report.finalize()

        with tempfile.TemporaryDirectory() as tmpdir:
            path = report.to_markdown(Path(tmpdir) / "summary.md")
            assert path.exists()

            content = path.read_text()
            assert "Total samples" in content
            assert "syntax_error" in content
            assert "no_relevance" in content

    def test_empty_report(self):
        report = NoiseReport(total_samples=0)
        report.finalize()
        assert report.removal_rate == 0.0
        assert report.kept_samples == 0
