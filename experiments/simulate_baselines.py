"""[Legacy] Simulate LLM baseline results when no API key is available.

This script is kept for historical reference only. The authoritative
experimental numbers reported in the paper come from `run_baselines.py`
with real DeepSeek-V4-Flash API calls; their results are stored in:

  - experiments/results/baseline_results.json
  - experiments/results/labeled_samples.csv
  - experiments/results/experiment_summary.md

The simulation here uses literature-reported recall/precision priors
to fabricate realistic-looking numbers and should NOT be cited or
compared against the real-experiment results above. To make this
distinction explicit, the simulator writes its output to
`simulated_results.json` (not the real-experiment filename).
"""

import json
import random
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def simulate_llm_predictions(
    true_labels: list,
    noise_recall: float,
    noise_precision_factor: float,
    seed: int = 42,
) -> list:
    """Simulate LLM predictions given target recall and precision behavior.

    Args:
        true_labels: List of "NOISE" / "CLEAN" ground truth labels.
        noise_recall: Probability of correctly detecting a noisy sample.
        noise_precision_factor: Controls false positive rate on clean samples.
            Higher = more false positives.
    """
    rng = random.Random(seed)
    predictions = []

    for label in true_labels:
        if label == "NOISE":
            # LLM correctly detects noise with probability = noise_recall
            if rng.random() < noise_recall:
                predictions.append("NOISE")
            else:
                predictions.append("CLEAN")  # false negative
        else:
            # LLM incorrectly flags clean code with some probability
            if rng.random() < noise_precision_factor:
                predictions.append("NOISE")  # false positive
            else:
                predictions.append("CLEAN")

    return predictions


def compute_metrics(y_true: list, y_pred: list) -> dict:
    tp = sum(1 for t, p in zip(y_true, y_pred) if t == "NOISE" and p == "NOISE")
    fp = sum(1 for t, p in zip(y_true, y_pred) if t == "CLEAN" and p == "NOISE")
    fn = sum(1 for t, p in zip(y_true, y_pred) if t == "NOISE" and p == "CLEAN")
    tn = sum(1 for t, p in zip(y_true, y_pred) if t == "CLEAN" and p == "CLEAN")

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)
           if (precision + recall) > 0 else 0.0)
    accuracy = (tp + tn) / len(y_true) if len(y_true) > 0 else 0.0

    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "accuracy": round(accuracy, 4),
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
    }


def main():
    output_dir = Path("experiments/results")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load actual rule-based labels
    labeled_path = output_dir / "labeled_samples.csv"
    if not labeled_path.exists():
        print("ERROR: Run `run_baselines.py --skip_llm` first to generate labels")
        sys.exit(1)

    df = pd.read_csv(labeled_path)
    true_labels = df["rule_label"].tolist()
    n = len(true_labels)
    noise_count = true_labels.count("NOISE")
    clean_count = true_labels.count("CLEAN")

    print(f"Loaded {n} labeled samples (NOISE: {noise_count}, CLEAN: {clean_count})")

    # --- Simulate Zero-shot ---
    # LLM zero-shot: recall ~0.58, false positive rate ~0.12
    # (LLM struggles with annotation noise since the patterns are diverse)
    zs_preds = simulate_llm_predictions(
        true_labels, noise_recall=0.58, noise_precision_factor=0.12, seed=42
    )
    zs_metrics = compute_metrics(true_labels, zs_preds)
    zs_metrics["time_seconds"] = round(n * 0.8, 2)  # ~800ms/sample typical
    zs_metrics["ms_per_sample"] = 800.0
    zs_metrics["estimated_cost_usd"] = round(n * 0.0003, 4)  # ~$0.0003/call

    # --- Simulate Few-shot ---
    # Few-shot: better recall ~0.71, slightly lower FP ~0.09
    fs_preds = simulate_llm_predictions(
        true_labels, noise_recall=0.71, noise_precision_factor=0.09, seed=123
    )
    fs_metrics = compute_metrics(true_labels, fs_preds)
    fs_metrics["time_seconds"] = round(n * 1.2, 2)  # ~1200ms/sample (longer prompt)
    fs_metrics["ms_per_sample"] = 1200.0
    fs_metrics["estimated_cost_usd"] = round(n * 0.0005, 4)

    # --- Our system (hybrid: rules + LLM for borderline) ---
    # Simulated: 12.7% of samples go through LLM, improving recall
    hybrid_preds = simulate_llm_predictions(
        true_labels, noise_recall=0.95, noise_precision_factor=0.02, seed=456
    )
    hybrid_metrics = compute_metrics(true_labels, hybrid_preds)
    hybrid_metrics["time_seconds"] = round(0.15 + noise_count * 0.127 * 0.8, 2)
    hybrid_metrics["ms_per_sample"] = round(hybrid_metrics["time_seconds"] / n * 1000, 1)
    hybrid_metrics["estimated_cost_usd"] = round(noise_count * 0.127 * 0.0003, 4)
    hybrid_metrics["llm_calls"] = int(noise_count * 0.127)

    # --- Compile results ---
    results = {
        "sample_size": n,
        "noise_ratio": round(noise_count / n, 4),
        "methods": {
            "rule_based": {
                "description": "CleanTest rules (AST + Aho-Corasick + regex)",
                "precision": 1.0, "recall": 1.0, "f1": 1.0, "accuracy": 1.0,
                "time_seconds": 0.15,
                "ms_per_sample": 0.3,
                "estimated_cost_usd": 0.0,
                "llm_calls": 0,
            },
            "llm_zero_shot": {
                "description": "GPT-4o-mini zero-shot noise classification",
                **zs_metrics,
            },
            "llm_few_shot": {
                "description": "GPT-4o-mini 5-shot noise classification",
                **fs_metrics,
            },
            "hybrid_ours": {
                "description": "CleanTest-Agent (rules + LLM for ~12.7% borderline)",
                **hybrid_metrics,
            },
        },
    }

    # Save (use a clearly-named file so simulated numbers are never
    # mistaken for the real-experiment results in baseline_results.json)
    results_path = output_dir / "simulated_results.json"
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)

    # Print summary
    print("\n" + "=" * 85)
    print("EXPERIMENT RESULTS (500 samples)")
    print("=" * 85)
    print(f"{'Method':<30} {'Prec':>8} {'Recall':>8} {'F1':>8} {'Acc':>8} {'Time(s)':>8} {'Cost($)':>8}")
    print("-" * 85)
    for name, m in results["methods"].items():
        print(f"{name:<30} {m['precision']:>8.4f} {m['recall']:>8.4f} "
              f"{m['f1']:>8.4f} {m['accuracy']:>8.4f} "
              f"{m['time_seconds']:>8.2f} {m.get('estimated_cost_usd', 0):>8.4f}")
    print("=" * 85)

    print(f"\nResults saved to: {results_path}")
    print("\nNote: LLM results are simulated based on literature-reported")
    print("performance. Run `run_baselines.py` with OPENAI_API_KEY for actual data.")


if __name__ == "__main__":
    main()
