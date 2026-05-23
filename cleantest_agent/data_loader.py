"""Dataset loading and validation utilities."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Union

import pandas as pd

REQUIRED_COLUMNS = {"src_fm", "target"}


def load_csv(path: Union[str, Path]) -> pd.DataFrame:
    """Load a CSV dataset and validate required columns.

    Raises ValueError if required columns are missing.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")
    if not path.suffix == ".csv":
        raise ValueError(f"Expected CSV file, got: {path.suffix}")

    df = pd.read_csv(path, low_memory=False)

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(
            f"Missing required columns: {missing}. "
            f"Available columns: {list(df.columns)}"
        )

    return df


def save_csv(
    df: pd.DataFrame,
    path: Union[str, Path],
    columns: Optional[List[str]] = None,
) -> Path:
    """Save a DataFrame to CSV.

    Args:
        df: DataFrame to save.
        path: Output path.
        columns: Optional subset of columns to include.

    Returns:
        The output Path.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if columns:
        df = df[columns]

    df.to_csv(path, index=False)
    return path
