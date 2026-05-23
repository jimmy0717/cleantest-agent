"""Unit tests for coverage prediction filter."""

import pandas as pd
import pytest

from cleantest_agent.pipeline import run_coverage_filter
from cleantest_agent.report_generator import NoiseReport


class TestCoverageFilter:
    def _make_df(self, coverages):
        """Helper to create a DataFrame with coverage values."""
        return pd.DataFrame({
            "src_fm": ["code"] * len(coverages),
            "target": ["test"] * len(coverages),
            "condition_cover_rate": coverages,
        })

    def test_removes_low_coverage(self):
        df = self._make_df([0.1, 0.2, 0.5, 0.8, 0.9])
        report = NoiseReport(total_samples=len(df))
        remove_idx = run_coverage_filter(df, report, threshold=0.3)
        # 0.1 and 0.2 should be removed
        assert len(remove_idx) == 2
        assert report.breakdown.get("low_coverage") == 2

    def test_keeps_all_above_threshold(self):
        df = self._make_df([0.5, 0.6, 0.7, 0.8])
        report = NoiseReport(total_samples=len(df))
        remove_idx = run_coverage_filter(df, report, threshold=0.3)
        assert len(remove_idx) == 0

    def test_removes_all_below_threshold(self):
        df = self._make_df([0.0, 0.1, 0.2])
        report = NoiseReport(total_samples=len(df))
        remove_idx = run_coverage_filter(df, report, threshold=0.3)
        assert len(remove_idx) == 3

    def test_skips_without_coverage_column(self):
        df = pd.DataFrame({
            "src_fm": ["code"],
            "target": ["test"],
        })
        report = NoiseReport(total_samples=len(df))
        remove_idx = run_coverage_filter(df, report)
        assert len(remove_idx) == 0  # gracefully skip
