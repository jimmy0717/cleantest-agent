"""Noise report generation utilities."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, Union


@dataclass
class NoiseReport:
    """Structured noise detection report."""

    total_samples: int = 0
    removed_samples: int = 0
    kept_samples: int = 0
    breakdown: Dict[str, int] = field(default_factory=dict)
    llm_calls: int = 0
    llm_overrides: int = 0  # times LLM said "KEEP" overriding a rule

    @property
    def removal_rate(self) -> float:
        if self.total_samples == 0:
            return 0.0
        return self.removed_samples / self.total_samples

    def add_noise(self, noise_type: str, count: int = 1):
        """Record noise detections by type."""
        self.breakdown[noise_type] = self.breakdown.get(noise_type, 0) + count
        self.removed_samples += count

    def finalize(self):
        """Compute kept_samples after all noise is recorded."""
        self.kept_samples = self.total_samples - self.removed_samples

    def to_json(self, path: Union[str, Path]) -> Path:
        """Write report as JSON."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = asdict(self)
        data["removal_rate"] = f"{self.removal_rate:.2%}"
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        return path

    def to_markdown(self, path: Union[str, Path]) -> Path:
        """Write report as Markdown summary."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        lines = [
            "# CleanTest-Agent Noise Report\n",
            f"- **Total samples**: {self.total_samples}",
            f"- **Removed**: {self.removed_samples} ({self.removal_rate:.2%})",
            f"- **Kept**: {self.kept_samples}",
            f"- **LLM calls**: {self.llm_calls}",
            f"- **LLM overrides (KEEP)**: {self.llm_overrides}",
            "",
            "## Breakdown by Noise Type\n",
            "| Noise Type | Count |",
            "|------------|-------|",
        ]
        for ntype, count in sorted(
            self.breakdown.items(), key=lambda x: -x[1]
        ):
            lines.append(f"| {ntype} | {count} |")

        with open(path, "w") as f:
            f.write("\n".join(lines) + "\n")
        return path
