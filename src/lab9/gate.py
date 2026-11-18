"""CI gate: compare a PR eval report with the main-branch baseline using the metric spec.

    python -m lab9.gate --pr reports/eval_workflow.json --baseline reports/baseline_v1.json

exit 0 = merge, exit 1 = blocked. Safety metrics: max 0, no averaging away.
Capability metrics: meet the floor AND the paired CI of (PR - main) is not entirely below 0.
Thresholds may only get stricter on the same eval-set version (ratchet).
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from lab8.console import utf8_stdio
from lab9 import stats
from lab9.eval import SPEC, load_spec, per_item


def integrity_check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> list[str]:
    """M7 (Expert): refuse to compare reports that cannot be trusted. Return a list of problems
    (empty = trustworthy). A gate that passes a broken report is worse than no gate.
    Must catch at least:
      - any metric value in pr["metrics"] that is NaN or inf
      - len(pr["rows"]) != manifest items x len(manifest seeds)   (dropped / duplicated rows)
      - the (item_id, seed) set of PR differs from the baseline's (cherry-picked seeds/items)
      - pr["evaluator_failures"] non-empty, or a row whose value for a graded spec metric is
        None (a crashed grader silently scores as "missing" and drops out of the mean)
      - base_spec given and a threshold in spec is LOOSER than in base_spec for the same
        eval-set version (ratchet: max may not rise, min may not fall, a blocking metric may
        not become non-blocking, a metric may not disappear; the same for spec["slices"],
        including dropping no_significant_drop)
      - an item's slice tags in PR rows differ from the baseline's (relabelling an item out of a
        slice hides its regression from the slice gate)"""
    problems: list[str] = []
    for name, value in (pr.get("metrics") or {}).items():
        if isinstance(value, (int, float)) and not math.isfinite(value):
            problems.append(f"metric {name} is not finite ({value})")

    def rows_by_pair(report: dict, label: str) -> dict[tuple[str, int], dict]:
        rows = report.get("rows") or []
        manifest = report.get("manifest") or {}
        want = int(manifest.get("items", 0)) * len(manifest.get("seeds") or [])
        if len(rows) != want:
            problems.append(f"{label} row count {len(rows)} != manifest items × seeds ({want})")
        pairs: dict[tuple[str, int], dict] = {}
        for row in rows:
            try:
                pair = (str(row["item_id"]), int(row["seed"]))
            except (KeyError, TypeError, ValueError):
                problems.append(f"{label} row missing a valid item_id/seed")
                continue
            if pair in pairs:
                problems.append(f"{label} duplicate row {pair[0]}@{pair[1]}")
            pairs[pair] = row
        return pairs

    pr_pairs = rows_by_pair(pr, "PR")
    base_pairs = rows_by_pair(base, "baseline")
    if set(pr_pairs) != set(base_pairs):
        problems.append("PR (item_id, seed) set differs from baseline")
    if pr.get("evaluator_failures"):
        problems.append(f"PR has {len(pr['evaluator_failures'])} evaluator failure(s)")

    from lab9.graders import GRADERS
    graded = {m["id"] for m in spec.get("metrics", []) if m.get("id") in GRADERS}
    for pair, row in pr_pairs.items():
        for metric in graded:
            if metric not in row or row[metric] is None:
                problems.append(f"PR row {pair[0]}@{pair[1]} has missing {metric}")
    for pair in set(pr_pairs) & set(base_pairs):
        pr_slices = set(pr_pairs[pair].get("slices") or [])
        base_slices = set(base_pairs[pair].get("slices") or [])
        if pr_slices != base_slices:
            problems.append(f"slice tags differ for {pair[0]}@{pair[1]}")

    if base_spec and spec.get("eval_set_version") == base_spec.get("eval_set_version"):
        old_metrics = {m["id"]: m for m in base_spec.get("metrics", [])}
        new_metrics = {m["id"]: m for m in spec.get("metrics", [])}
        for mid, old in old_metrics.items():
            new = new_metrics.get(mid)
            if new is None:
                problems.append(f"ratchet: metric {mid} was removed")
                continue
            old_th, new_th = old.get("threshold") or {}, new.get("threshold") or {}
            if "min" in old_th and ("min" not in new_th or new_th["min"] < old_th["min"]):
                problems.append(f"ratchet: metric {mid} min threshold was loosened")
            if "max" in old_th and ("max" not in new_th or new_th["max"] > old_th["max"]):
                problems.append(f"ratchet: metric {mid} max threshold was loosened")
            if "max_increase" in old_th and (
                    "max_increase" not in new_th or new_th["max_increase"] > old_th["max_increase"]):
                problems.append(f"ratchet: metric {mid} max_increase threshold was loosened")
            if old_th.get("no_significant_drop") and not new_th.get("no_significant_drop"):
                problems.append(f"ratchet: metric {mid} dropped no_significant_drop")
            if old.get("blocking") and not new.get("blocking"):
                problems.append(f"ratchet: metric {mid} is no longer blocking")

        old_slices = {s["name"]: s for s in base_spec.get("slices", [])}
        new_slices = {s["name"]: s for s in spec.get("slices", [])}
        for name, old in old_slices.items():
            new = new_slices.get(name)
            if new is None:
                problems.append(f"ratchet: slice {name} was removed")
                continue
            if old.get("metric") != new.get("metric"):
                problems.append(f"ratchet: slice {name} metric was changed")
            if "min" in old and ("min" not in new or new["min"] < old["min"]):
                problems.append(f"ratchet: slice {name} min threshold was loosened")
            if old.get("no_significant_drop") and not new.get("no_significant_drop"):
                problems.append(f"ratchet: slice {name} dropped no_significant_drop")
            if old.get("blocking") and not new.get("blocking"):
                problems.append(f"ratchet: slice {name} is no longer blocking")
    return problems


def slice_check(pr: dict, base: dict, spec: dict) -> tuple[list[str], list[str]]:
    """M5 (Advanced): an average can hide a regression on a small, important slice.
    For each entry of spec["slices"] ({"name", "metric", "min"?, "no_significant_drop"?, "blocking"}):
      - value = mean of per_item(pr, metric, slice_name=name)
      - fail if below "min", or if no_significant_drop and the paired CI over the slice's items
        lies entirely below 0
    Return (blocked ids like "slice:money_movement/pass_rate", report lines)."""
    blocked: list[str] = []
    lines: list[str] = []
    bs = spec.get("bootstrap", {})
    for entry in spec.get("slices", []):
        name, metric = entry["name"], entry["metric"]
        pr_items = per_item(pr, metric, name)
        base_items = per_item(base, metric, name)
        sid = f"slice:{name}/{metric}"
        if not pr_items:
            failed = True
            value = None
            note = "no PR rows in slice"
        else:
            value = sum(pr_items.values()) / len(pr_items)
            failed = "min" in entry and value < entry["min"]
            note = ""
        if entry.get("no_significant_drop"):
            common = sorted(set(pr_items) & set(base_items))
            if not common:
                failed = True
                note = (note + "; " if note else "") + "no paired items in baseline slice"
            else:
                d, lo, hi = stats.paired_bootstrap(
                    [pr_items[k] for k in common], [base_items[k] for k in common],
                    n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027),
                    confidence=bs.get("confidence", 0.95))
                note = (note + "; " if note else "") + f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
                if hi < 0:
                    failed = True
        label = "BLOCK" if failed and entry.get("blocking") else ("warn" if failed else "ok")
        lines.append(f"  {sid:<38} {value!s:<8} {note:<30} {label}")
        if failed and entry.get("blocking"):
            blocked.append(sid)
    return blocked, lines


def check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> tuple[list[str], list[str]]:
    if pr["manifest"]["eval_set_sha"] != base["manifest"]["eval_set_sha"]:
        return ["eval_set_sha"], ["  EVAL SET differs from the baseline's: re-run the baseline on the same eval set"]
    problems = integrity_check(pr, base, spec, base_spec)
    if problems:
        return ["integrity"], [f"  INTEGRITY {p}" for p in problems]
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for m in spec["metrics"]:
        mid, th, val = m["id"], m.get("threshold", {}), pr["metrics"].get(m["id"])
        verdict, note = "ok", ""
        if val is None:
            verdict = "missing"
        elif "max" in th and val > th["max"]:
            verdict = "fail"
        elif "min" in th and val < th["min"]:
            verdict = "fail"
        elif "max_increase" in th and base["metrics"].get(mid):
            if val > base["metrics"][mid] * (1 + th["max_increase"]):
                verdict = "fail"
        if th.get("no_significant_drop") and val is not None:
            a, b = per_item(pr, mid), per_item(base, mid)
            keys = sorted(set(a) & set(b))
            d, lo, hi = stats.paired_bootstrap([a[k] for k in keys], [b[k] for k in keys],
                                               n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027))
            note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
            if hi < 0:
                verdict = "fail"
        if verdict != "ok" and m.get("blocking"):
            blocked.append(mid)
        label = {"ok": "ok", "missing": "MISSING"}.get(verdict, "BLOCK" if m.get("blocking") else "warn")
        lines.append(f"  {mid:<22} {val!s:<8} {json.dumps(th):<40} {note:<28} {label}")
    if spec.get("slices"):
        sb, sl = slice_check(pr, base, spec)
        blocked += sb
        lines += sl
    return blocked, lines


def main(argv: list[str] | None = None) -> int:
    utf8_stdio()
    ap = argparse.ArgumentParser(prog="lab9.gate")
    ap.add_argument("--pr", required=True)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--spec", default=str(SPEC))
    ap.add_argument("--base-spec", help="metric spec on main, for the ratchet check (M7)")
    args = ap.parse_args(argv)
    pr = json.loads(Path(args.pr).read_text(encoding="utf-8"))
    base = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    base_spec = load_spec(Path(args.base_spec)) if args.base_spec else None
    blocked, lines = check(pr, base, load_spec(Path(args.spec)), base_spec)
    print(f"gate: PR {pr['run_id']} vs main {base['run_id']} · eval set {pr['manifest']['eval_set_sha']}")
    print("\n".join(lines))
    if blocked:
        print(f"exit 1 — blocked: {', '.join(blocked)}")
        return 1
    print("exit 0 — merge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
