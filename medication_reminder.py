"""Simple medication reminder for seniors.

This module provides a command line utility that reads a JSON configuration
and periodically reminds the user when it is time to take medication.
"""
from __future__ import annotations

import argparse
import json
import signal
import sys
import textwrap
import time as time_module
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Iterable, Sequence


@dataclass(frozen=True)
class Medication:
    """Describes one medication and its intake schedule."""

    name: str
    dosage: str | None
    times: Sequence[time]
    notes: str | None = None


@dataclass(frozen=True)
class Reminder:
    """Represents a single reminder instance for a medication."""

    medication: Medication
    due: datetime


def parse_time_string(value: str) -> time:
    """Parse a ``HH:MM`` formatted string into a :class:`datetime.time`.

    Parameters
    ----------
    value:
        Time string in ``HH:MM`` format, using 24-hour notation.

    Returns
    -------
    datetime.time
        The parsed time of day.

    Raises
    ------
    ValueError
        If the provided value is not a valid time.
    """

    try:
        hours, minutes = value.split(":", maxsplit=1)
        return time(hour=int(hours), minute=int(minutes))
    except ValueError as exc:  # pragma: no cover - defensive path
        raise ValueError(f"Invalid time value '{value}'. Expected HH:MM format.") from exc


def load_configuration(path: Path) -> tuple[list[Medication], int]:
    """Load medication configuration from ``path``.

    The configuration file must be JSON with the following structure::

        {
            "check_interval_minutes": 1,
            "medications": [
                {
                    "name": "降压药",
                    "dosage": "1片",
                    "times": ["08:00", "20:00"],
                    "notes": "饭后服用"
                }
            ]
        }

    Parameters
    ----------
    path:
        Path to the JSON configuration file.

    Returns
    -------
    tuple[list[Medication], int]
        The loaded medication list and the polling interval in minutes.

    Raises
    ------
    FileNotFoundError
        If the configuration file does not exist.
    ValueError
        If the configuration file is invalid.
    """

    data = json.loads(path.read_text(encoding="utf-8"))

    medications_data = data.get("medications", [])
    if not isinstance(medications_data, list) or not medications_data:
        raise ValueError("Configuration must contain a non-empty 'medications' list.")

    medications: list[Medication] = []
    for index, entry in enumerate(medications_data, start=1):
        if not isinstance(entry, dict):
            raise ValueError(f"Medication entry #{index} is not an object.")

        try:
            name = entry["name"].strip()
        except KeyError as exc:
            raise ValueError(f"Medication entry #{index} is missing a 'name' field.") from exc
        if not name:
            raise ValueError(f"Medication entry #{index} has an empty name.")

        times_field = entry.get("times")
        if not isinstance(times_field, Sequence) or not times_field:
            raise ValueError(f"Medication '{name}' must define at least one intake time.")
        times = [parse_time_string(str(t)) for t in times_field]

        dosage = entry.get("dosage")
        dosage = str(dosage).strip() if dosage else None
        notes = entry.get("notes")
        notes = str(notes).strip() if notes else None

        medications.append(Medication(name=name, dosage=dosage, times=tuple(times), notes=notes))

    interval = data.get("check_interval_minutes", 1)
    try:
        interval = int(interval)
    except (TypeError, ValueError) as exc:  # pragma: no cover - defensive path
        raise ValueError("'check_interval_minutes' must be an integer.") from exc
    if interval <= 0:
        raise ValueError("'check_interval_minutes' must be a positive integer.")

    return medications, interval


def next_occurrence(time_of_day: time, reference: datetime) -> datetime:
    """Return the next occurrence of ``time_of_day`` after ``reference``."""

    candidate = datetime.combine(reference.date(), time_of_day)
    if candidate <= reference:
        candidate += timedelta(days=1)
    return candidate


def build_initial_schedule(medications: Iterable[Medication], now: datetime) -> list[Reminder]:
    """Create the first reminder for each medication/time combination."""

    schedule: list[Reminder] = []
    for medication in medications:
        for moment in medication.times:
            schedule.append(Reminder(medication=medication, due=next_occurrence(moment, now)))
    schedule.sort(key=lambda reminder: reminder.due)
    return schedule


def format_medication_message(medication: Medication) -> str:
    """Create a human-friendly reminder message."""

    parts: list[str] = [f"现在是服用 {medication.name} 的时间！"]
    if medication.dosage:
        parts.append(f"剂量：{medication.dosage}")
    if medication.notes:
        parts.append(f"备注：{medication.notes}")
    return "\n".join(parts)


def print_upcoming_schedule(reminders: Sequence[Reminder], days: int = 1) -> None:
    """Print the schedule for the next ``days`` days."""

    horizon = datetime.now() + timedelta(days=days)
    print("接下来需要服药的时间：")
    for reminder in reminders:
        if reminder.due <= horizon:
            print(f"  - {reminder.due:%Y-%m-%d %H:%M} → {reminder.medication.name}")


def reminder_loop(reminders: list[Reminder], interval_minutes: int) -> None:
    """Continuously check and display reminders."""

    if not reminders:
        print("没有可用的服药提醒。请检查配置文件。")
        return

    interval_seconds = max(30, interval_minutes * 60)
    print("提醒程序已启动。按 Ctrl+C 退出。")

    def handle_sigint(signum, frame):  # pragma: no cover - involves signal handling
        print("\n已停止提醒程序。保持健康！")
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_sigint)

    while True:
        now = datetime.now()
        reminders.sort(key=lambda reminder: reminder.due)
        next_reminder = reminders[0]
        if next_reminder.due <= now:
            message = format_medication_message(next_reminder.medication)
            print("\a")  # Audible bell for emphasis.
            print("=" * 40)
            print(f"提醒时间：{next_reminder.due:%Y-%m-%d %H:%M}")
            print(message)
            print("=" * 40)
            # Schedule the same reminder for the next day.
            updated = Reminder(medication=next_reminder.medication, due=next_reminder.due + timedelta(days=1))
            reminders[0] = updated
        else:
            wait_seconds = min(interval_seconds, max(5, (next_reminder.due - now).total_seconds()))
            time_module.sleep(wait_seconds)


def create_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="一个帮助老年人定时服药的提醒小程序",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(
            """
            配置示例（保存为 medications.json）：

                {
                    "check_interval_minutes": 1,
                    "medications": [
                        {
                            "name": "降压药",
                            "dosage": "1片",
                            "times": ["08:00", "20:00"],
                            "notes": "饭后服用"
                        },
                        {
                            "name": "维生素D",
                            "dosage": "2滴",
                            "times": ["09:00"],
                            "notes": "晒完太阳后服用"
                        }
                    ]
                }
            """
        ),
    )
    parser.add_argument(
        "config",
        type=Path,
        help="包含服药计划的 JSON 配置文件路径",
    )
    parser.add_argument(
        "--preview-days",
        type=int,
        default=1,
        help="启动前展示的天数安排，默认展示 1 天",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = create_argument_parser()
    args = parser.parse_args(argv)

    try:
        medications, interval = load_configuration(args.config)
    except (FileNotFoundError, ValueError) as exc:
        parser.error(str(exc))

    reminders = build_initial_schedule(medications, datetime.now())
    print_upcoming_schedule(reminders, days=max(1, args.preview_days))
    reminder_loop(reminders, interval)
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
