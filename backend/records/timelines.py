"""Alberta notice dates from the Residential Tenancies Act, ss. 7–10, 14, 23, 29 and 30.

The served date is the date service was actually effected. The current Act
requires personal service or registered mail and does not add extra days for mail.
"""

from datetime import date, datetime, time, timedelta

from django.utils import timezone

from deposits.alberta_calendar import ALBERTA_HOLIDAYS, add_years


def shift_months(day: date, months: int) -> date:
    month_index = day.month - 1 + months
    year = day.year + month_index // 12
    month = month_index % 12 + 1
    if month == 12:
        last = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last = date(year, month + 1, 1) - timedelta(days=1)
    return date(year, month, min(day.day, last.day))


def tenancy_month_start(day: date, due_day: int) -> date:
    if day.day >= due_day:
        return day.replace(day=due_day)
    previous = shift_months(day.replace(day=1), -1)
    return date(previous.year, previous.month, due_day)


def tenancy_month_end(start: date) -> date:
    return shift_months(start, 1) - timedelta(days=1)


def week_start(day: date, weekday: int) -> date:
    return day - timedelta(days=(day.weekday() - weekday) % 7)


def earliest_monthly_end(served: date, due_day: int, months: int) -> date:
    """Last day of a notice period of `months` tenancy months.

    Service on the first day of a tenancy month counts that month.
    A later day waits for the next tenancy month (s. 10, late notice).
    """
    start = tenancy_month_start(served, due_day)
    if served > start:
        start = shift_months(start, 1)
    return tenancy_month_end(shift_months(start, months - 1))


def is_monthly_end(day: date, due_day: int) -> bool:
    return day == tenancy_month_end(tenancy_month_start(day, due_day))


def earliest_weekly_end(served: date, week_starts: int) -> date:
    start = week_start(served, week_starts)
    if served > start:
        start = start + timedelta(days=7)
    return start + timedelta(days=6)


def is_weekly_end(day: date, week_starts: int) -> bool:
    return day == week_start(day, week_starts) + timedelta(days=6)


def tenancy_year_ends(start: date, after: date, horizon_years: int = 8) -> list[date]:
    ends = []
    for index in range(1, horizon_years + 1):
        end = add_years(start, index) - timedelta(days=1)
        if end > after:
            ends.append(end)
    return ends


def earliest_rent_increase(served: date, period: str, due_day: int, week_starts: int) -> date:
    if period == 'weekly':
        start = week_start(served, week_starts)
        if served > start:
            start = start + timedelta(days=7)
        return start + timedelta(weeks=12)
    if period == 'monthly':
        start = tenancy_month_start(served, due_day)
        if served > start:
            start = shift_months(start, 1)
        return shift_months(start, 3)
    return served + timedelta(days=90)


def entry_allowed(day: date, at: time) -> str:
    if day.weekday() == 6 or day in ALBERTA_HOLIDAYS:
        return 'Entry with notice cannot be on a Sunday or a holiday. The holiday list covers 2025 through 2027.'
    if at < time(8, 0) or at > time(20, 0):
        return 'Entry with notice has to fall between 8:00 a.m. and 8:00 p.m.'
    return ''


def as_time(value) -> time | None:
    if value in (None, ''):
        return None
    if isinstance(value, time):
        return value
    text = str(value).strip()
    if len(text) == 5:
        text = f'{text}:00'
    return datetime.strptime(text, '%H:%M:%S').time()


def aware(day: date, at: time) -> datetime:
    combined = datetime.combine(day, at)
    if timezone.is_naive(combined):
        return timezone.make_aware(combined, timezone.get_current_timezone())
    return combined
