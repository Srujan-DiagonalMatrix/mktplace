from __future__ import annotations

from pathlib import Path

import yaml

DOC_PATH = Path("docs/delivery-checklist-v1.md")

REQUIRED_SECTION_HEADERS = [
    "## In-Scope Demo Capabilities",
    "## Out-of-Scope (Explicit)",
    "## Required Acceptance Criteria by Module",
    "## KPI Definitions (Measurable)",
    "## Traceability Matrix",
    "## Baseline v1 Demo Script (Freeze)",
]

REQUIRED_KPI_KEYS = {
    "conversation_completion_rate",
    "drop_off_rate_by_stage",
    "pain_point_detection_coverage",
    "sentiment_distribution_quality",
}


def _extract_yaml_block(markdown: str) -> str:
    lines = markdown.splitlines()
    in_block = False
    collected: list[str] = []
    for line in lines:
        if line.strip() == "```yaml":
            in_block = True
            continue
        if in_block and line.strip() == "```":
            break
        if in_block:
            collected.append(line)
    return "\n".join(collected).strip()


def _existing_reference(path_token: str) -> bool:
    token = path_token.strip().strip("`")
    if not token:
        return True
    if token.endswith("/"):
        return Path(token).is_dir()
    return Path(token).exists()


def test_delivery_doc_contains_required_sections_and_script_steps():
    content = DOC_PATH.read_text(encoding="utf-8")

    for header in REQUIRED_SECTION_HEADERS:
        assert header in content, f"Missing required section: {header}"

    for step in [
        "1. **Start session**",
        "4. **Recommendation gate**",
        "7. **Enquiry gate**",
        "9. **Health gate**",
    ]:
        assert step in content, f"Missing required demo script step: {step}"


def test_kpi_schema_contains_required_metric_definitions():
    content = DOC_PATH.read_text(encoding="utf-8")
    yaml_block = _extract_yaml_block(content)
    assert yaml_block, "KPI YAML block is missing"

    parsed = yaml.safe_load(yaml_block)
    assert "kpi_schema" in parsed
    schema = parsed["kpi_schema"]
    assert schema["version"] == 1
    assert schema["windows"]["aggregation_period"] == "daily"

    metrics = schema.get("metrics", {})
    assert REQUIRED_KPI_KEYS.issubset(metrics.keys())

    completion = metrics["conversation_completion_rate"]
    assert "formula" in completion and "/" in completion["formula"]

    dropoff = metrics["drop_off_rate_by_stage"]
    assert isinstance(dropoff.get("stages"), list)
    assert len(dropoff["stages"]) >= 3

    sentiment = metrics["sentiment_distribution_quality"]
    assert isinstance(sentiment.get("checks"), list)
    assert len(sentiment["checks"]) >= 3


def test_traceability_matrix_references_existing_paths_only():
    content = DOC_PATH.read_text(encoding="utf-8")
    matrix_lines = [
        line
        for line in content.splitlines()
        if line.startswith("| ") and not line.startswith("|---")
    ]
    assert len(matrix_lines) >= 3, "Traceability matrix rows are missing"

    # skip header row
    for row in matrix_lines[1:]:
        columns = [col.strip() for col in row.split("|")[1:-1]]
        assert len(columns) == 5, f"Unexpected matrix column count: {row}"

        for col in columns[1:]:
            refs = [item.strip() for item in col.split(";")]
            for ref in refs:
                assert _existing_reference(ref), f"Missing path in matrix: {ref}"
