"""Integration tests for the full pipeline."""

import tempfile
from pathlib import Path

import pytest

from cleantest_agent.pipeline import run_pipeline


class TestPipeline:
    @pytest.fixture
    def sample_csv(self):
        """Path to the noisy sample fixture."""
        return str(
            Path(__file__).parent / "fixtures" / "sample_noisy.csv"
        )

    @pytest.fixture
    def clean_csv(self):
        """Path to the clean sample fixture."""
        return str(
            Path(__file__).parent / "fixtures" / "sample_clean.csv"
        )

    def test_pipeline_runs_without_error(self, sample_csv):
        with tempfile.TemporaryDirectory() as tmpdir:
            report = run_pipeline(
                input_csv=sample_csv,
                output_dir=tmpdir,
                llm_enhance=False,
                skip_coverage=True,
            )
            assert report.total_samples > 0
            assert report.kept_samples >= 0
            assert report.removed_samples >= 0
            assert report.total_samples == (
                report.kept_samples + report.removed_samples
            )

            # Check output files exist
            assert (Path(tmpdir) / "filtered_data.csv").exists()
            assert (Path(tmpdir) / "noise_report.json").exists()
            assert (Path(tmpdir) / "summary.md").exists()

    def test_pipeline_removes_some_noise(self, sample_csv):
        with tempfile.TemporaryDirectory() as tmpdir:
            report = run_pipeline(
                input_csv=sample_csv,
                output_dir=tmpdir,
                llm_enhance=False,
                skip_coverage=True,
            )
            # sample_noisy.csv has intentional noise samples
            assert report.removed_samples > 0

    def test_pipeline_clean_data_minimal_removal(self, clean_csv):
        with tempfile.TemporaryDirectory() as tmpdir:
            report = run_pipeline(
                input_csv=clean_csv,
                output_dir=tmpdir,
                llm_enhance=False,
                skip_coverage=True,
            )
            # Clean data should have very few removals
            assert report.removal_rate < 0.5  # Less than 50% removed

    def test_report_structure(self, sample_csv):
        with tempfile.TemporaryDirectory() as tmpdir:
            report = run_pipeline(
                input_csv=sample_csv,
                output_dir=tmpdir,
                llm_enhance=False,
                skip_coverage=True,
            )
            assert isinstance(report.breakdown, dict)
            assert report.llm_calls == 0  # LLM not enabled
            assert report.llm_overrides == 0
