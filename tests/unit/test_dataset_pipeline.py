from __future__ import annotations

import json

from src.backend.services.ai.dataset_pipeline import (
    REQUIRED_DATASETS,
    build_data_quality_report,
    canonicalize_preference_row,
    normalize_nulls,
    split_by_conversation,
    validate_dataset_inventory,
)


def _seed_interaction_files(base):
    for filename in REQUIRED_DATASETS.values():
        target = base / filename
        if filename.endswith(".jsonl"):
            target.write_text("", encoding="utf-8")
        elif filename.endswith(".csv"):
            target.write_text("id,value\n", encoding="utf-8")
        else:
            target.write_text("# labeling", encoding="utf-8")


def test_validate_dataset_inventory_requires_all_files(tmp_path):
    _seed_interaction_files(tmp_path)
    inventory = validate_dataset_inventory(tmp_path)
    assert set(inventory.keys()) == set(REQUIRED_DATASETS.keys())


def test_normalize_nulls_standardizes_tokens():
    rows = [{"a": "NULL", "b": "n/a", "c": "ok", "d": ""}]
    assert normalize_nulls(rows) == [{"a": None, "b": None, "c": "ok", "d": None}]


def test_canonicalize_preference_row_maps_aliases():
    ontology = [
        {"attribute": "fuel_type", "canonical_value": "Petrol", "aliases": "petrol|gasoline"},
        {"attribute": "transmission", "canonical_value": "Automatic", "aliases": "automatic|auto"},
    ]
    row = {"fuel_type": "gasoline", "transmission": "auto"}
    normalized = canonicalize_preference_row(row, ontology)
    assert normalized["fuel_type"] == "Petrol"
    assert normalized["transmission"] == "Automatic"


def test_split_by_conversation_is_group_safe():
    rows = [
        {"conversation_id": "c1", "x": 1},
        {"conversation_id": "c1", "x": 2},
        {"conversation_id": "c2", "x": 3},
    ]
    splits = split_by_conversation(rows, train_ratio=0.5)
    train_ids = {r["conversation_id"] for r in splits["train"]}
    test_ids = {r["conversation_id"] for r in splits["test"]}
    assert train_ids.isdisjoint(test_ids)


def test_build_data_quality_report_counts_rows_dupes_and_missing(tmp_path):
    _seed_interaction_files(tmp_path)
    (tmp_path / "conversation_turns.jsonl").write_text(
        "\n".join(
            [
                json.dumps({"conversation_id": "c1", "user_message": "hello", "target_slot_gold": ""}),
                json.dumps({"conversation_id": "c1", "user_message": "hello", "target_slot_gold": ""}),
            ]
        ),
        encoding="utf-8",
    )
    (tmp_path / "preference_ground_truth.csv").write_text(
        "sample_id,fuel_type\n1,\n2,petrol\n",
        encoding="utf-8",
    )
    report = build_data_quality_report(tmp_path)
    assert report.rows_by_dataset["conversation_turns"] == 2
    assert report.duplicates["conversation_turns"] == 1
    assert report.missing_required_fields["conversation_turns"] == 2
    assert report.rows_by_dataset["preference_ground_truth"] == 2
