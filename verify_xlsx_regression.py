"""Reproduce the monthly-sales false rejection using the bundled OSWorld evaluator."""
from __future__ import annotations

import hashlib
import json
import sys
from importlib import import_module
from importlib.metadata import version
from pathlib import Path
from types import ModuleType

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parent
UPSTREAM = ROOT / "data/osworld"
METRICS = UPSTREAM / "desktop_env/evaluators/metrics"
TASK_ID = "26a8440e-c166-4c50-aef4-bfb77314b46b"
TASK = UPSTREAM / f"evaluation_examples/examples/libreoffice_calc/{TASK_ID}.json"
ASSETS = ROOT / "data/sample_files/monthly_sales_regression"
OUT = ROOT / "output/xlsx_regression.json"


def load_upstream_metric():
    # Import table and its utility module without the desktop package's eager
    # loading of unrelated browser, PDF, and virtual machine dependencies.
    for folder in (UPSTREAM / "desktop_env", METRICS.parent, METRICS):
        name = ".".join(folder.relative_to(UPSTREAM).parts)
        if name not in sys.modules:
            package = ModuleType(name)
            package.__path__ = [str(folder)]
            sys.modules[name] = package
    return import_module("desktop_env.evaluators.metrics.table").compare_table


def nonempty_rows(sheet):
    return [row for row in sheet.values if any(value is not None for value in row)]


def sales_totals(source):
    workbook = load_workbook(source, read_only=True, data_only=True)
    try:
        header, *records = nonempty_rows(workbook["Sheet1"])
        if header[0] != "Sales Rep" or len(set(header[1:])) != len(header[1:]):
            raise ValueError("Unexpected source headers")
        return {month: sum(row[index] for row in records)
                for index, month in enumerate(header[1:], start=1)}
    finally:
        workbook.close()


def monthly_records(artifact):
    workbook = load_workbook(artifact, read_only=True, data_only=True)
    try:
        if "Sheet2" not in workbook.sheetnames:
            return []
        return nonempty_rows(workbook["Sheet2"])
    finally:
        workbook.close()


def monthly_table_is_correct(rows, expected):
    if not rows or rows[0] != ("Month", "Total") or len(rows) != len(expected) + 1:
        return False
    if any(len(row) != 2 or type(row[1]) not in (int, float) for row in rows[1:]):
        return False
    return dict(rows[1:]) == expected


def fingerprint(path):
    return {"path": path.relative_to(ROOT).as_posix(),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def main():
    task = json.loads(TASK.read_text(encoding="utf-8"))
    evaluator = task["evaluator"]
    if evaluator["func"] != "compare_table":
        raise ValueError("Task no longer uses compare_table")
    rules = evaluator["options"]["rules"]
    preserve_rules = [rule for rule in rules if rule["type"] == "preserve_cells"]
    if len(preserve_rules) != 1 or {rule["type"] for rule in rules} != {"sheet_data", "preserve_cells"}:
        raise ValueError("The task's original checks have changed")
    original = load_upstream_metric()
    source = ASSETS / "input.xlsx"
    gold = ASSETS / "chronological.xlsx"
    expected = sales_totals(source)
    cases = {}
    for name, expected_scores in (
        ("chronological", (1, 1)),
        ("reverse", (0, 1)),
        ("incorrect_total", (0, 0)),
    ):
        artifact = ASSETS / f"{name}.xlsx"
        rows = monthly_records(artifact)
        matches = monthly_table_is_correct(rows, expected)
        kept_source = original(str(artifact), str(source), rules=preserve_rules)
        upstream = original(str(artifact), str(gold), **evaluator["options"])
        repaired = int(matches and kept_source == 1)
        if (upstream, repaired) != expected_scores or kept_source != 1:
            raise AssertionError(f"{name}: original={upstream}, local={repaired}, preserved={kept_source}")
        cases[name] = {
            "artifact": fingerprint(artifact), "rows": rows[1:],
            "source_sheet_score": kept_source, "month_totals_match": matches,
            "upstream_score": upstream, "repaired_score": repaired,
        }
        print(f"{name}: original={upstream}, local={repaired}")

    chronological = cases["chronological"]["rows"]
    reverse = cases["reverse"]["rows"]
    bad = cases["incorrect_total"]["rows"]
    if reverse != chronological[::-1] or bad[1:] != reverse[1:] or bad[0] != (reverse[0][0], reverse[0][1] + 1):
        raise AssertionError("The controls must change only order or one monthly total")

    report = {
        "scope": "offline comparison of spreadsheet artifacts",
        "metric": fingerprint(METRICS / "table.py"),
        "dependencies": {name: version(name) for name in ("openpyxl", "pandas", "rapidfuzz", "formulas", "xmltodict", "cssselect", "lxml", "tldextract")},
        "tasks": {TASK_ID: {
            "task": fingerprint(TASK), "input": fingerprint(source), "expected_asset": evaluator["expected"],
            "input_asset": task["config"][0]["parameters"]["files"][0]["url"],
            "rules": rules, "totals_from_source": expected, "cases": cases,
        }},
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
