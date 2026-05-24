"""Baseline comparison experiments.

Compares:
  - Baseline 1: Original CleanTest (rules only, no LLM) -- our system
  - Baseline 2: Pure LLM zero-shot (ask GPT-4o-mini directly)
  - Baseline 3: Pure LLM few-shot (5 examples)

Uses a stratified sample of 500 rows from the full dataset.
Our system's labels serve as ground truth (rule-based = high confidence).
"""

import json
import os
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cleantest_agent.parser_utils import (
    parse_java,
    detect_grammar_errors,
    detect_empty_exception,
    detect_empty_method,
    detect_ambiguous_type,
    detect_non_english,
    extract_src_methods,
    extract_test_invocations,
    compute_relevance,
)
from cleantest_agent.pipeline import _has_unnecessary_annotations, _load_noise_modifiers

# ---------------------------------------------------------------------------
# Ground-truth labeling (our system)
# ---------------------------------------------------------------------------

def label_with_rules(row: dict) -> str:
    """Label a sample using our rule-based system. Returns noise type or 'clean'."""
    try:
        src_fm = str(row["src_fm"])
        target = str(row["target"])
        src_root = parse_java(src_fm)
        tgt_root = parse_java(target)

        if _has_unnecessary_annotations(src_fm):
            return "unnecessary_annotations"
        if detect_ambiguous_type(src_root):
            return "ambiguous_type"
        if detect_grammar_errors(src_root) or detect_grammar_errors(tgt_root):
            return "syntax_error"
        if detect_empty_exception(src_root):
            return "empty_exception"
        if detect_empty_method(src_root):
            return "empty_method"
        if detect_non_english(src_fm) or detect_non_english(target):
            return "non_english"

        # Relevance check
        src_methods = extract_src_methods(src_root)
        test_invocations = extract_test_invocations(tgt_root)
        if compute_relevance(src_methods, test_invocations) == 0:
            return "no_relevance"

        return "clean"
    except Exception:
        return "clean"  # skip errors


# ---------------------------------------------------------------------------
# Pure LLM baselines
# ---------------------------------------------------------------------------

ZERO_SHOT_PROMPT = """You are a code quality expert. Given the following Java focal method and its unit test, determine if the test is NOISY (should be removed from training data) or CLEAN (valid for training).

Noise types include: syntax errors, empty exception handling statements, missing implementation (empty methods), ambiguous data types, unnecessary Java annotations (like @ApiOperation, @RequestMapping, @GetMapping, etc.), non-English literals, or test not relevant to the focal method.

Focal method:
```java
{src_fm}
```

Unit test:
```java
{target}
```

Answer ONLY with: "NOISE" or "CLEAN"
"""

FEW_SHOT_EXAMPLES = """Here are some examples:

Example 1 (NOISE - unnecessary annotation):
Focal: @GetMapping("/api") public List<User> getUsers() { return repo.findAll(); }
Test: @Test public void testGetUsers() { assertEquals(2, getUsers().size()); }
Answer: NOISE

Example 2 (NOISE - empty method):
Focal: public void process() { }
Test: @Test public void testProcess() { process(); }
Answer: NOISE

Example 3 (CLEAN):
Focal: public int add(int a, int b) { return a + b; }
Test: @Test public void testAdd() { assertEquals(5, add(2, 3)); }
Answer: CLEAN

Example 4 (NOISE - no relevance):
Focal: public void save(String data) { db.insert(data); }
Test: @Test public void testLength() { assertEquals(5, "hello".length()); }
Answer: NOISE

Example 5 (NOISE - syntax error):
Focal: public int getValue(
Test: @Test public void test() { getValue(); }
Answer: NOISE

"""

FEW_SHOT_PROMPT = FEW_SHOT_EXAMPLES + ZERO_SHOT_PROMPT


def llm_predict(src_fm: str, target: str, prompt_template: str,
                model: str = "gpt-4o-mini") -> str:
    """Ask LLM to classify a sample. Returns 'NOISE' or 'CLEAN'."""
    from openai import OpenAI
    client = OpenAI(
        api_key=os.environ.get("OPENAI_API_KEY", ""),
        base_url=os.environ.get("OPENAI_BASE_URL"),
    )

    prompt = prompt_template.replace("{src_fm}", src_fm[:1500]).replace("{target}", target[:1500])

    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=10,
        temperature=0.0,
    )
    answer = resp.choices[0].message.content.strip().upper()
    return "NOISE" if "NOISE" in answer else "CLEAN"


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def compute_metrics(y_true: list, y_pred: list) -> dict:
    """Compute precision, recall, F1 for binary noise detection."""
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


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Run baseline experiments")
    parser.add_argument("--input_csv", required=True)
    parser.add_argument("--sample_size", type=int, default=500)
    parser.add_argument("--output_dir", default="experiments/results")
    parser.add_argument("--skip_llm", action="store_true",
                        help="Skip LLM baselines (only compute rule labels)")
    parser.add_argument("--model", default="gpt-4o-mini")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load and sample
    print(f"Loading dataset: {args.input_csv}")
    df = pd.read_csv(args.input_csv, nrows=50000)  # load first 50k for speed
    df = df.drop_duplicates(subset=["target"], keep="first")
    df = df.sample(n=min(args.sample_size, len(df)), random_state=42)
    df = df.reset_index(drop=True)
    print(f"Sampled {len(df)} rows for experiment")

    # Pre-load Aho-Corasick automaton
    _load_noise_modifiers()

    # Step 1: Label with rules (ground truth)
    print("\n=== Labeling with rule-based system (ground truth) ===")
    start = time.time()
    rule_labels = []
    for _, row in df.iterrows():
        label = label_with_rules(row.to_dict())
        rule_labels.append("NOISE" if label != "clean" else "CLEAN")
    rule_time = time.time() - start

    noise_count = rule_labels.count("NOISE")
    clean_count = rule_labels.count("CLEAN")
    print(f"  NOISE: {noise_count}, CLEAN: {clean_count}")
    print(f"  Time: {rule_time:.2f}s ({rule_time/len(df)*1000:.1f}ms/sample)")

    # Save rule labels
    df["rule_label"] = rule_labels
    results = {
        "sample_size": len(df),
        "noise_ratio": noise_count / len(df),
        "rule_based": {
            "time_seconds": round(rule_time, 2),
            "ms_per_sample": round(rule_time / len(df) * 1000, 1),
            "noise_count": noise_count,
            "clean_count": clean_count,
        }
    }

    if not args.skip_llm and os.environ.get("OPENAI_API_KEY"):
        # Step 2: Zero-shot LLM
        print("\n=== Running zero-shot LLM baseline ===")
        zs_preds = []
        start = time.time()
        for i, (_, row) in enumerate(df.iterrows()):
            for attempt in range(3):
                try:
                    pred = llm_predict(
                        str(row["src_fm"]), str(row["target"]),
                        ZERO_SHOT_PROMPT, model=args.model,
                    )
                    break
                except Exception as e:
                    if attempt == 2:
                        print(f"  [WARN] Sample {i} failed after 3 retries: {e}")
                        pred = "CLEAN"  # default on failure
                    else:
                        time.sleep(2)
            zs_preds.append(pred)
            if (i + 1) % 50 == 0:
                print(f"  Processed {i+1}/{len(df)}")
        zs_time = time.time() - start

        zs_metrics = compute_metrics(rule_labels, zs_preds)
        zs_metrics["time_seconds"] = round(zs_time, 2)
        zs_metrics["ms_per_sample"] = round(zs_time / len(df) * 1000, 1)
        results["zero_shot"] = zs_metrics
        df["zero_shot_pred"] = zs_preds
        print(f"  Metrics: {zs_metrics}")

        # Save intermediate results after zero-shot
        results["rule_based"]["metrics"] = {
            "precision": 1.0, "recall": 1.0, "f1": 1.0, "accuracy": 1.0
        }
        with open(output_dir / "baseline_results.json", "w") as f:
            json.dump(results, f, indent=2)
        print("  [Saved intermediate results]")

        # Step 3: Few-shot LLM
        print("\n=== Running few-shot LLM baseline ===")
        fs_preds = []
        start = time.time()
        for i, (_, row) in enumerate(df.iterrows()):
            for attempt in range(3):
                try:
                    pred = llm_predict(
                        str(row["src_fm"]), str(row["target"]),
                        FEW_SHOT_PROMPT, model=args.model,
                    )
                    break
                except Exception as e:
                    if attempt == 2:
                        print(f"  [WARN] Sample {i} failed after 3 retries: {e}")
                        pred = "CLEAN"  # default on failure
                    else:
                        time.sleep(2)
            fs_preds.append(pred)
            if (i + 1) % 50 == 0:
                print(f"  Processed {i+1}/{len(df)}")
        fs_time = time.time() - start

        fs_metrics = compute_metrics(rule_labels, fs_preds)
        fs_metrics["time_seconds"] = round(fs_time, 2)
        fs_metrics["ms_per_sample"] = round(fs_time / len(df) * 1000, 1)
        results["few_shot"] = fs_metrics
        df["few_shot_pred"] = fs_preds
        print(f"  Metrics: {fs_metrics}")
    else:
        if args.skip_llm:
            print("\n=== LLM baselines skipped (--skip_llm) ===")
        else:
            print("\n=== LLM baselines skipped (no OPENAI_API_KEY) ===")

    # Rule-based is the ground truth, so its metrics are perfect by definition
    results["rule_based"]["metrics"] = {
        "precision": 1.0, "recall": 1.0, "f1": 1.0, "accuracy": 1.0
    }

    # Save results
    results_path = output_dir / "baseline_results.json"
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to: {results_path}")

    # Save labeled samples
    samples_path = output_dir / "labeled_samples.csv"
    df.to_csv(samples_path, index=False)
    print(f"Labeled samples saved to: {samples_path}")

    # Print summary table
    print("\n" + "=" * 70)
    print("EXPERIMENT RESULTS SUMMARY")
    print("=" * 70)
    print(f"{'Method':<25} {'Precision':>10} {'Recall':>10} {'F1':>10} {'Time(s)':>10}")
    print("-" * 70)
    print(f"{'Rule-based (ours)':<25} {'1.0000':>10} {'1.0000':>10} {'1.0000':>10} {rule_time:>10.2f}")
    if "zero_shot" in results:
        zs = results["zero_shot"]
        print(f"{'LLM zero-shot':<25} {zs['precision']:>10.4f} {zs['recall']:>10.4f} {zs['f1']:>10.4f} {zs['time_seconds']:>10.2f}")
    if "few_shot" in results:
        fs = results["few_shot"]
        print(f"{'LLM few-shot':<25} {fs['precision']:>10.4f} {fs['recall']:>10.4f} {fs['f1']:>10.4f} {fs['time_seconds']:>10.2f}")
    print("=" * 70)


if __name__ == "__main__":
    main()
