from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CuratedPolicyPrior:
    assistant_action: str
    target_slot: str | None
    weight: float


class CuratedInteractionAdapter:
    def __init__(self, base_dir: Path | str | None = None):
        root = Path(base_dir) if base_dir else Path(__file__).resolve().parents[4] / "data" / "interaction"
        self._policy_rows = self._read_jsonl(root / "dialogue_policy_labels.jsonl")
        self._turn_rows = self._read_jsonl(root / "conversation_turns.jsonl")

    @staticmethod
    def _read_jsonl(path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        rows: list[dict[str, Any]] = []
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line:
                continue
            rows.append(json.loads(line))
        return rows

    @property
    def is_available(self) -> bool:
        return bool(self._policy_rows or self._turn_rows)

    def get_policy_priors(self, *, preferences: dict[str, Any], hesitation_count: int, last_question_key: str | None = None) -> list[CuratedPolicyPrior]:
        missing_required = [k for k in ("fuel_type", "transmission", "monthly_from_gbp") if preferences.get(k) in (None, "")]
        sentiment = str(preferences.get("sentiment") or "").lower() or None
        score: dict[tuple[str, str | None], float] = {}
        for row in self._policy_rows:
            state = row.get("state") or {}
            if set(state.get("missing_required_slots") or []) != set(missing_required):
                continue
            if int(state.get("hesitation_count") or 0) != int(hesitation_count):
                continue
            if last_question_key and state.get("last_question_key") and state.get("last_question_key") != last_question_key:
                continue
            if sentiment and state.get("sentiment_label") and str(state.get("sentiment_label")).lower() != sentiment:
                continue
            key = (str(row.get("gold_action") or ""), row.get("gold_target_slot"))
            score[key] = score.get(key, 0.0) + 1.0
        total = sum(score.values())
        if total <= 0:
            return []
        return [CuratedPolicyPrior(assistant_action=k[0], target_slot=k[1], weight=v / total) for k, v in sorted(score.items(), key=lambda i: i[1], reverse=True)]

    def get_few_shot_exemplars(self, *, preferences: dict[str, Any], hesitation_count: int, max_items: int = 3) -> list[dict[str, Any]]:
        missing_required = [k for k in ("fuel_type", "transmission", "monthly_from_gbp") if preferences.get(k) in (None, "")]
        out: list[dict[str, Any]] = []
        for row in self._turn_rows:
            row_prefs = row.get("preferences") or {}
            row_missing = [k for k in ("fuel_type", "transmission", "monthly_from_gbp") if row_prefs.get(k) in (None, "")]
            if set(row_missing) != set(missing_required):
                continue
            if int(row.get("hesitation_count") or 0) != int(hesitation_count):
                continue
            out.append({
                "user_message": row.get("message"),
                "expected_action": row.get("expected_action"),
                "expected_next_slot": row.get("expected_next_slot"),
            })
            if len(out) >= max_items:
                break
        return out
