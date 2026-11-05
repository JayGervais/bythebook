"""Banking days for the two-day security-deposit trust deadline.

Weekends and a short list of Alberta statutory holidays are skipped.
Dates outside 2025–2027 fall back to weekends only. Confirm the holiday
list each year before you rely on a reminder.
"""

from datetime import date, timedelta

ALBERTA_HOLIDAYS = {
    # 2025
    date(2025, 1, 1),
    date(2025, 2, 17),
    date(2025, 4, 18),
    date(2025, 5, 19),
    date(2025, 7, 1),
    date(2025, 8, 4),
    date(2025, 9, 1),
    date(2025, 9, 30),
    date(2025, 10, 13),
    date(2025, 11, 11),
    date(2025, 12, 25),
    date(2025, 12, 26),
    # 2026
    date(2026, 1, 1),
    date(2026, 2, 16),
    date(2026, 4, 3),
    date(2026, 5, 18),
    date(2026, 7, 1),
    date(2026, 8, 3),
    date(2026, 9, 7),
    date(2026, 9, 30),
    date(2026, 10, 12),
    date(2026, 11, 11),
    date(2026, 12, 25),
    date(2026, 12, 26),
    # 2027
    date(2027, 1, 1),
    date(2027, 2, 15),
    date(2027, 3, 26),
    date(2027, 5, 24),
    date(2027, 7, 1),
    date(2027, 8, 2),
    date(2027, 9, 6),
    date(2027, 9, 30),
    date(2027, 10, 11),
    date(2027, 11, 11),
    date(2027, 12, 25),
    date(2027, 12, 27),  # Boxing Day observed, 26 Dec 2027 is a Sunday
}


def is_banking_day(day: date) -> bool:
    return day.weekday() < 5 and day not in ALBERTA_HOLIDAYS


def add_banking_days(start: date, days: int) -> date:
    current = start
    added = 0
    while added < days:
        current += timedelta(days=1)
        if is_banking_day(current):
            added += 1
    return current


def add_years(day: date, years: int) -> date:
    try:
        return day.replace(year=day.year + years)
    except ValueError:
        return day.replace(year=day.year + years, day=28)
