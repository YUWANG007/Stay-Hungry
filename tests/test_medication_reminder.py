from __future__ import annotations

from datetime import datetime, time
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import json

import pytest

from medication_reminder import (
    Medication,
    build_initial_schedule,
    load_configuration,
    next_occurrence,
    parse_time_string,
)


def test_parse_time_string_parses_valid_values() -> None:
    assert parse_time_string("08:15") == time(8, 15)
    assert parse_time_string("23:59") == time(23, 59)


def test_next_occurrence_returns_same_day_if_future() -> None:
    reference = datetime(2023, 1, 1, 8, 0)
    assert next_occurrence(time(9, 0), reference) == datetime(2023, 1, 1, 9, 0)


def test_next_occurrence_rolls_to_next_day_if_needed() -> None:
    reference = datetime(2023, 1, 1, 21, 0)
    assert next_occurrence(time(9, 0), reference) == datetime(2023, 1, 2, 9, 0)


def test_build_initial_schedule_sorts_reminders() -> None:
    meds = [
        Medication(name="A", dosage=None, times=(time(8, 0), time(20, 0))),
        Medication(name="B", dosage=None, times=(time(7, 0),)),
    ]
    schedule = build_initial_schedule(meds, datetime(2023, 1, 1, 6, 0))
    assert [reminder.medication.name for reminder in schedule] == ["B", "A", "A"]
    assert schedule[0].due == datetime(2023, 1, 1, 7, 0)


def test_load_configuration_reads_json_file(tmp_path: Path) -> None:
    config = {
        "check_interval_minutes": 2,
        "medications": [
            {
                "name": "降压药",
                "dosage": "1片",
                "times": ["08:00", "20:00"],
                "notes": "饭后服用",
            }
        ],
    }
    config_path = tmp_path / "medications.json"
    config_path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")

    medications, interval = load_configuration(config_path)

    assert interval == 2
    assert len(medications) == 1
    med = medications[0]
    assert med.name == "降压药"
    assert med.dosage == "1片"
    assert med.times == (time(8, 0), time(20, 0))
    assert med.notes == "饭后服用"


def test_load_configuration_requires_medications(tmp_path: Path) -> None:
    config_path = tmp_path / "medications.json"
    config_path.write_text(json.dumps({"medications": []}), encoding="utf-8")

    with pytest.raises(ValueError):
        load_configuration(config_path)
