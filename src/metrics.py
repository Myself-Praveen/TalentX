import json
from typing import Dict, Any

def normalize_arg(val):
    if val is None:
        return ""
    if isinstance(val, (int, float)):
        return str(val)
    return str(val).lower().strip()

def is_semantically_equivalent(exp_val, act_val, expected_key=None):
    if exp_val == act_val:
        return True
        
    if exp_val is None and act_val is not None:
        return False
    if act_val is None and exp_val is not None:
        return False

    exp_str = str(exp_val).strip().lower()
    act_str = str(act_val).strip().lower()
    
    if exp_str == act_str:
        return True

    # Numeric coercion for amounts (e.g. 5000 vs "5000" vs 5000.0)
    if "amount" in str(expected_key).lower() or isinstance(exp_val, (int, float)):
        try:
            return float(exp_val) == float(act_val)
        except (ValueError, TypeError):
            pass
            
    # For borrower_statement or notes, we allow a strict word overlap check since it's free-text
    if expected_key in ["borrower_statement", "notes"]:
        exp_words = set([w for w in exp_str.split() if len(w) > 3])
        if not exp_words:
            return act_str != ""
        act_words = set(act_str.split())
        overlap = len(exp_words.intersection(act_words))
        if len(exp_words) > 0 and overlap / len(exp_words) >= 0.3:
            return True
        return False

    return False

def calculate_metrics(results: list[dict]) -> dict:
    """
    results: List of dictionaries with structure:
    {
        "id": str,
        "language": str,
        "expected_tool": str | None,
        "expected_args": dict | None,
        "actual_tool": str | None,
        "actual_args": dict | None,
        "error": str | None
    }
    """
    from collections import defaultdict
    metrics = {
        "english": {"total": 0, "correct_tool": 0, "malformed_args": 0, "spurious": 0, "missed": 0, "wrong_tool": 0, "total_latency": 0, "latency_count": 0, "confusion": defaultdict(int)},
        "hinglish": {"total": 0, "correct_tool": 0, "malformed_args": 0, "spurious": 0, "missed": 0, "wrong_tool": 0, "total_latency": 0, "latency_count": 0, "confusion": defaultdict(int)},
        "marathi": {"total": 0, "correct_tool": 0, "malformed_args": 0, "spurious": 0, "missed": 0, "wrong_tool": 0, "total_latency": 0, "latency_count": 0, "confusion": defaultdict(int)}
    }
    
    for row in results:
        lang = row["language"].lower()
        if lang not in metrics:
            continue
            
        metrics[lang]["total"] += 1
        if "latency_ms" in row:
            metrics[lang]["total_latency"] += row["latency_ms"]
            metrics[lang]["latency_count"] += 1
        
        expected_tool = row["expected_tool"]
        actual_tool = row["actual_tool"]
        
        # Track confusion matrix for ALL cases
        exp_t = expected_tool if expected_tool else "NONE"
        act_t = actual_tool if actual_tool else "NONE"
        metrics[lang]["confusion"][f"{exp_t} -> {act_t}"] += 1
        
        # 1. Missed Call
        if expected_tool is not None and expected_tool != "NONE" and (actual_tool is None or actual_tool == "NONE"):
            metrics[lang]["missed"] += 1
            continue
            
        # 2. Spurious Call
        if (expected_tool is None or expected_tool == "NONE") and actual_tool is not None and actual_tool != "NONE":
            metrics[lang]["spurious"] += 1
            continue
            
        # 3. Wrong Tool
        if expected_tool is not None and expected_tool != "NONE" and actual_tool is not None and actual_tool != "NONE" and expected_tool != actual_tool:
            metrics[lang]["wrong_tool"] += 1
            continue
            
        # 4. Correct Tool (Selection only)
        if expected_tool == actual_tool:
            metrics[lang]["correct_tool"] += 1
            
            # 5. Malformed / Incorrect Arguments
            if row.get("error"):
                metrics[lang]["malformed_args"] += 1
            elif expected_tool and expected_tool != "NONE":
                exp_args = row.get("expected_args", {})
                act_args = row.get("actual_args", {})
                
                # Check semantic equivalence for all keys
                for k, v in exp_args.items():
                    act_val = act_args.get(k)
                    if not is_semantically_equivalent(v, act_val, expected_key=k):
                        metrics[lang]["malformed_args"] += 1
                        break

    return metrics

def print_report(metrics: dict):
    print("=" * 50)
    print("EVALUATION RESULTS (Delta Report)")
    print("=" * 50)
    
    for lang in ["english", "hinglish", "marathi"]:
        m = metrics[lang]
        total = m["total"]
        if total == 0:
            continue
        
        tool_acc = (m["correct_tool"] / total) * 100
        spurious_rate = (m["spurious"] / total) * 100
        missed_rate = (m["missed"] / total) * 100
        wrong_tool_rate = (m["wrong_tool"] / total) * 100
        malformed_rate = (m["malformed_args"] / total) * 100
        avg_latency = (m["total_latency"] / m["latency_count"]) if m["latency_count"] > 0 else 0
        
        print(f"--- {lang.upper()} ---")
        print(f"Total Cases:         {total}")
        print(f"Correct Tool Rate:   {tool_acc:.1f}%")
        print(f"Wrong Tool Rate:     {wrong_tool_rate:.1f}%")
        print(f"Spurious Calls:      {spurious_rate:.1f}%")
        print(f"Missed Calls:        {missed_rate:.1f}%")
        print(f"Malformed Arguments: {malformed_rate:.1f}%")
        if avg_latency > 0:
            print(f"Average Latency:     {avg_latency:.0f} ms")
        print()
        
        print("Top Confusions (Expected -> Actual):")
        sorted_conf = sorted(m["confusion"].items(), key=lambda x: x[1], reverse=True)
        for pair, count in sorted_conf:
            exp_t, act_t = pair.split(" -> ")
            if exp_t != act_t and count > 1:
                print(f"  {pair}: {count} times")
        print("\n")
        
    print("Delta Analysis:")
    if metrics["english"]["total"] > 0 and metrics["hinglish"]["total"] > 0:
        eng_acc = (metrics["english"]["correct_tool"] / metrics["english"]["total"]) * 100
        hin_acc = (metrics["hinglish"]["correct_tool"] / metrics["hinglish"]["total"]) * 100
        print(f"English vs Hinglish Degradation (Tool Accuracy): {eng_acc - hin_acc:.1f}%")
        
    if metrics["english"]["total"] > 0 and metrics["marathi"]["total"] > 0:
        eng_acc = (metrics["english"]["correct_tool"] / metrics["english"]["total"]) * 100
        mar_acc = (metrics["marathi"]["correct_tool"] / metrics["marathi"]["total"]) * 100
        print(f"English vs Marathi Degradation (Tool Accuracy): {eng_acc - mar_acc:.1f}%")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        metrics = calculate_metrics(data)
        print_report(metrics)
    else:
        print("Usage: python metrics.py <results.json>")
