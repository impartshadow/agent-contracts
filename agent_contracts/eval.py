"""Evaluate contract behavior against labeled JSONL records."""

from __future__ import annotations

from typing import Any, Iterable

from .core import Registry
from .replay import replay_records


def _safe_ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def evaluate_records(records: Iterable[dict[str, Any]], registry: Registry) -> dict[str, Any]:
    """Replay labeled records and return precision/recall-style metrics.

    Each record may include:

    - ``expected_blocked``: whether a BLOCK violation should fire.
    - ``expected_contracts``: contract names that should fire on the record.

    Unlabeled records are still replayed but excluded from the block confusion
    matrix.
    """

    materialized = list(records)
    rows = replay_records(materialized, registry)
    labeled_rows: list[dict[str, Any]] = []
    true_positive = true_negative = false_positive = false_negative = 0
    contract_misses: list[dict[str, Any]] = []

    for record, row in zip(materialized, rows):
        expected_blocked = record.get("expected_blocked")
        expected_contracts = set(record.get("expected_contracts") or [])
        actual_contracts = {violation["contract"] for violation in row["violations"]}
        missing_contracts = sorted(expected_contracts - actual_contracts)
        unexpected_contracts = (
            sorted(actual_contracts - expected_contracts) if expected_contracts else []
        )

        if missing_contracts:
            contract_misses.append(
                {
                    "index": row["index"],
                    "line": row["line"],
                    "expected_contracts": sorted(expected_contracts),
                    "fired_contracts": sorted(actual_contracts),
                    "missing_contracts": missing_contracts,
                }
            )

        labeled = isinstance(expected_blocked, bool)
        row_result = dict(row)
        row_result["expected_blocked"] = expected_blocked
        row_result["expected_contracts"] = sorted(expected_contracts)
        row_result["missing_contracts"] = missing_contracts
        row_result["unexpected_contracts"] = unexpected_contracts
        row_result["labeled"] = labeled
        labeled_rows.append(row_result)

        if not labeled:
            continue
        if expected_blocked and row["blocked"]:
            true_positive += 1
        elif expected_blocked and not row["blocked"]:
            false_negative += 1
        elif not expected_blocked and row["blocked"]:
            false_positive += 1
        else:
            true_negative += 1

    precision = _safe_ratio(true_positive, true_positive + false_positive)
    recall = _safe_ratio(true_positive, true_positive + false_negative)
    accuracy = _safe_ratio(
        true_positive + true_negative,
        true_positive + true_negative + false_positive + false_negative,
    )

    return {
        "passed": false_positive == 0 and false_negative == 0 and not contract_misses,
        "records": len(rows),
        "labeled_records": sum(1 for row in labeled_rows if row["labeled"]),
        "true_positive": true_positive,
        "true_negative": true_negative,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "precision": precision,
        "recall": recall,
        "accuracy": accuracy,
        "contract_misses": contract_misses,
        "rows": labeled_rows,
    }
