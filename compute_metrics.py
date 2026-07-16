"""
Scores live /extract output (results/extract_<fir>.json, produced by
benchmark_runner.py) against exact ground truth from corpus_data.py.

"""

import json
import os
import re
import sys

sys.path.insert(0, ".")
from corpus_data import FIRS

RESULTS_DIR = "results"


def normalize(s):
    if s is None:
        return None
    return re.sub(r"[\s\-]", "", str(s)).lower()


def ground_truth_for_doc(d):
    """Exact expected identifier values, mirroring what generate_and_eval.py's
    gen_fir() actually wrote into the document text."""
    gt = {
        "phone_numbers": {"9000000000", "9988776655", "9012345678"},
        "vehicle_numbers": set(),
        "aadhaar_numbers": set(),
        "pan_numbers": set(),
        "ifsc_codes": set(),
        "passport_numbers": set(),
        "upi_ids": set(),
        "bank_accounts": set(),
        "driving_licences": set(),
        "imei_numbers": set(),
        "fir_number": {d["fir"]},
    }
    if d.get("mobile"):
        gt["phone_numbers"].add(d["mobile"])
    if d.get("vehicle_reg"):
        gt["vehicle_numbers"].add(d["vehicle_reg"])
    if d.get("aadhaar"):
        gt["aadhaar_numbers"].add(d["aadhaar"])
    if d.get("pan"):
        gt["pan_numbers"].add(d["pan"])
    if d.get("ifsc"):
        gt["ifsc_codes"].add(d["ifsc"])
    if d.get("passport"):
        gt["passport_numbers"].add(d["passport"])
    if d.get("upi"):
        gt["upi_ids"].add(d["upi"])
    if d.get("bank"):
        gt["bank_accounts"].add(d["bank"])
    if d.get("dl"):
        gt["driving_licences"].add(d["dl"])
    if d.get("imei"):
        gt["imei_numbers"].add(d["imei"])
    return gt


def score_identifiers():
    totals = {k: {"tp": 0, "fp": 0, "fn": 0} for k in
              ["phone_numbers", "vehicle_numbers", "aadhaar_numbers", "pan_numbers",
               "ifsc_codes", "passport_numbers", "upi_ids", "bank_accounts",
               "driving_licences", "imei_numbers", "fir_number"]}

    missing_files = []
    for d in FIRS:
        fname = f"{RESULTS_DIR}/extract_{d['fir'].replace('/', '_')}.json"
        if not os.path.exists(fname):
            missing_files.append(fname)
            continue
        with open(fname) as f:
            extracted = json.load(f)

        regex_entities = extracted.get("regex_entities", {})
        gt = ground_truth_for_doc(d)

        for key in totals:
            if key == "fir_number":
                extracted_vals = {regex_entities.get("fir_number")} if regex_entities.get("fir_number") else set()
            else:
                extracted_vals = set(regex_entities.get(key, []) or [])

            expected_norm = {normalize(x) for x in gt[key]}
            extracted_norm = {normalize(x) for x in extracted_vals}

            tp = len(expected_norm & extracted_norm)
            fp = len(extracted_norm - expected_norm)
            fn = len(expected_norm - extracted_norm)

            totals[key]["tp"] += tp
            totals[key]["fp"] += fp
            totals[key]["fn"] += fn

    if missing_files:
        print(f"WARNING: {len(missing_files)} extract result files not found "
              f"(e.g. {missing_files[0]}). Run benchmark_runner.py first.\n")

    print(f"{'Type':<20}{'TP':>5}{'FP':>5}{'FN':>5}{'Precision':>12}{'Recall':>10}{'F1':>8}")
    print("-" * 65)
    agg_tp = agg_fp = agg_fn = 0
    for key, c in totals.items():
        tp, fp, fn = c["tp"], c["fp"], c["fn"]
        agg_tp += tp; agg_fp += fp; agg_fn += fn
        precision = tp / (tp + fp) if (tp + fp) else float("nan")
        recall = tp / (tp + fn) if (tp + fn) else float("nan")
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) and precision == precision and recall == recall and (precision + recall) > 0 else float("nan")
        print(f"{key:<20}{tp:>5}{fp:>5}{fn:>5}{precision:>12.3f}{recall:>10.3f}{f1:>8.3f}")

    print("-" * 65)
    p = agg_tp / (agg_tp + agg_fp) if (agg_tp + agg_fp) else float("nan")
    r = agg_tp / (agg_tp + agg_fn) if (agg_tp + agg_fn) else float("nan")
    f1 = 2 * p * r / (p + r) if (p + r) > 0 else float("nan")
    print(f"{'OVERALL':<20}{agg_tp:>5}{agg_fp:>5}{agg_fn:>5}{p:>12.3f}{r:>10.3f}{f1:>8.3f}")


def score_contradictions():
    print("\n=== Contradiction Detection ===")
    # Ground truth: exactly which (entity, type, relation) combinations are the
    # real planted conflicts. Anything else returned counts as a false positive —
    # in particular, COMMITTED_<crime>_AT conflicts are a known systemic FP source
    # (the detector flags any repeat offender across locations, with no date check).
    true_positive_keys = {
        ("Vikram Reddy", "attribute_conflict", "age"),
        ("Vikram Reddy", "relation_conflict", "FLED_IN"),
        ("Ravi Kumar", "attribute_conflict", "mobile"),
        ("Priya Sharma", "temporal_spatial_conflict", None),
    }
    names = ["Vikram Reddy", "Ravi Kumar", "Priya Sharma"]

    tp = fp = 0
    tp_found = set()
    fp_details = []

    for name in names:
        fname = f"{RESULTS_DIR}/contradict_{name.replace(' ', '_')}.json"
        if not os.path.exists(fname):
            print(f"[{name}] no result file at {fname} — run benchmark_runner.py's contradiction check first")
            continue
        with open(fname) as f:
            result = json.load(f)
        contradictions = result.get("contradictions", [])
        print(f"\n[{name}]: {len(contradictions)} contradiction(s) returned")
        for c in contradictions:
            ctype = c.get("type")
            relation = c.get("relation") or c.get("attribute")
            key = (name, ctype, relation)
            is_tp = key in true_positive_keys
            label = "TRUE POSITIVE" if is_tp else "FALSE POSITIVE"
            print(f"    [{label}] type={ctype} relation/attr={relation}")
            if is_tp:
                tp += 1
                tp_found.add(key)
            else:
                fp += 1
                fp_details.append((name, ctype, relation))

    fn = len(true_positive_keys - tp_found)
    precision = tp / (tp + fp) if (tp + fp) else float("nan")
    recall = tp / (tp + fn) if (tp + fn) else float("nan")
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else float("nan")

    print(f"\nTP={tp}  FP={fp}  FN={fn}")
    print(f"Precision={precision:.3f}  Recall={recall:.3f}  F1={f1:.3f}")
    if fp_details:
        print("\nFalse positive pattern check — are these all the same root cause?")
        from collections import Counter
        pattern_counts = Counter((ctype, rel) for _, ctype, rel in fp_details)
        for (ctype, rel), count in pattern_counts.most_common():
            print(f"  {count}x  type={ctype} relation/attr={rel}")


if __name__ == "__main__":
    score_identifiers()
    score_contradictions()
