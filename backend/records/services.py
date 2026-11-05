from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from records.models import MaintenanceTask, RentPayment
from records.notices import BREACH_REASONS, SERVICE_LABELS, TERMINATION_REASONS, render_notice
from records.timelines import (
    as_time,
    aware,
    earliest_monthly_end,
    earliest_rent_increase,
    earliest_weekly_end,
    entry_allowed,
    is_monthly_end,
    is_weekly_end,
    tenancy_year_ends,
)


SCHEDULE = (
    ('furnace', 'Furnace service', 365, 'Have the furnace serviced about once a year.'),
    ('smoke_co', 'Smoke and CO alarms', 365, 'Check that smoke and carbon monoxide alarms are in place and working.'),
    ('filter', 'Furnace filter', 90, 'Replace or clean the furnace filter about every three months.'),
)


def ensure_schedule(unit):
    if unit.tasks.exists():
        return
    anchor = timezone.localtime(unit.created_at).date() if unit.created_at else timezone.localdate()
    MaintenanceTask.objects.bulk_create([
        MaintenanceTask(
            unit=unit,
            kind=kind,
            label=label,
            interval_days=days,
            next_due_on=anchor + timedelta(days=days),
            note=note,
        )
        for kind, label, days, note in SCHEDULE
    ])


def complete_task(task, done_on):
    task.last_done_on = done_on
    task.next_due_on = done_on + timedelta(days=task.interval_days)
    task.save(update_fields=['last_done_on', 'next_due_on'])
    return task


def next_receipt_number(tenancy) -> str:
    numbers = []
    for raw in tenancy.payments.values_list('receipt_number', flat=True):
        try:
            numbers.append(int(raw))
        except (TypeError, ValueError):
            continue
    return f'{(max(numbers) if numbers else 0) + 1:04d}'


@transaction.atomic
def record_payment(tenancy, amount, paid_on, method, note=''):
    return RentPayment.objects.create(
        tenancy=tenancy,
        amount=amount,
        paid_on=paid_on,
        method=method,
        note=(note or '')[:200],
        receipt_number=next_receipt_number(tenancy),
    )


def _require(payload, key, message):
    value = payload.get(key)
    if value in (None, ''):
        return message
    return ''


def prepare_notice(tenancy, payload):
    """Return (fields, error_dict). fields include the stored body."""
    kind = payload.get('kind') or ''
    served = payload.get('served_on')
    effective = payload.get('effective_on')
    method = payload.get('service_method') or ''
    errors = {}
    if kind not in ('terminate_periodic', 'substantial_breach', 'damage_or_assault', 'rent_increase', 'entry'):
        errors['kind'] = 'Choose a notice.'
    if served is None:
        errors['served_on'] = 'Add the date service was effected.'
    if effective is None:
        errors['effective_on'] = 'Add the effective date.'
    if method not in SERVICE_LABELS:
        errors['service_method'] = 'Choose how it was served. The Act starts with personal service or registered mail.'
    if errors:
        return None, errors

    reason_code = (payload.get('reason_code') or '').strip()
    reason = (payload.get('reason') or '').strip()
    new_rent = payload.get('new_rent')
    if new_rent in (None, ''):
        new_rent = None
    else:
        new_rent = Decimal(str(new_rent))
    try:
        served_time = as_time(payload.get('served_time'))
        effective_time = as_time(payload.get('effective_time'))
    except ValueError:
        return None, {'served_time': 'Use a time like 09:00.'}

    if kind == 'terminate_periodic':
        if tenancy.period == 'fixed':
            errors['kind'] = (
                'A fixed term ends on the date in the agreement. The Act does not require a termination notice for it.'
            )
        elif reason_code not in TERMINATION_REASONS:
            errors['reason_code'] = 'Choose the reason for ending the tenancy.'
        elif reason_code == 'other' and not reason:
            errors['reason'] = 'Write the prescribed reason.'
        else:
            _check_periodic_end(tenancy, served, effective, errors)
        if not reason and reason_code in TERMINATION_REASONS:
            reason = TERMINATION_REASONS[reason_code]

    elif kind == 'substantial_breach':
        if reason_code not in BREACH_REASONS:
            errors['reason_code'] = 'Say whether this is unpaid rent or another breach.'
        if not reason:
            errors['reason'] = 'Describe the breach, including the rent that is due if this is about non-payment.'
        elif effective < served + timedelta(days=14):
            errors['effective_on'] = 'A substantial-breach notice has to name a termination day at least 14 days after service.'

    elif kind == 'damage_or_assault':
        if not reason:
            errors['reason'] = 'Describe the damage, assault, or threat.'
        elif not served_time or not effective_time:
            errors['effective_time'] = 'Add the time of service and the time the tenancy ends. This notice needs 24 hours.'
        elif aware(effective, effective_time) < aware(served, served_time) + timedelta(hours=24):
            errors['effective_on'] = 'Serve this notice at least 24 hours before the termination time.'

    elif kind == 'rent_increase':
        if tenancy.period == 'fixed':
            errors['kind'] = 'Rent cannot be increased during a fixed term.'
        elif new_rent is None or new_rent <= tenancy.rent_amount:
            errors['new_rent'] = 'Enter a new rent that is higher than the current rent.'
        else:
            _check_rent_increase(tenancy, served, effective, errors)

    elif kind == 'entry':
        if not reason:
            errors['reason'] = 'State why you are entering.'
        elif not served_time or not effective_time:
            errors['effective_time'] = 'Name the time of service and the time of entry.'
        else:
            window = entry_allowed(effective, effective_time)
            if window:
                errors['effective_on'] = window
            elif aware(effective, effective_time) < aware(served, served_time) + timedelta(hours=24):
                errors['effective_on'] = 'Serve the notice at least 24 hours before the time of entry.'

    if errors:
        return None, errors

    fields = {
        'kind': kind,
        'served_on': served,
        'served_time': served_time,
        'effective_on': effective,
        'effective_time': effective_time,
        'service_method': method,
        'reason_code': reason_code,
        'reason': reason,
        'new_rent': new_rent if kind == 'rent_increase' else None,
    }
    notice = tenancy.notices.model(tenancy=tenancy, body='', **fields)
    fields['body'] = render_notice(notice)
    return fields, {}


def _check_periodic_end(tenancy, served, effective, errors):
    if tenancy.period == 'monthly':
        earliest = earliest_monthly_end(served, tenancy.rent_due_day, 3)
        if effective < earliest or not is_monthly_end(effective, tenancy.rent_due_day):
            errors['effective_on'] = (
                f'A landlord ends a monthly tenancy on the last day of a tenancy month, '
                f'after three tenancy months. The earliest date for service on {served.isoformat()} is {earliest.isoformat()}.'
            )
    elif tenancy.period == 'weekly':
        weekday = tenancy.start_date.weekday()
        earliest = earliest_weekly_end(served, weekday)
        if effective < earliest or not is_weekly_end(effective, weekday):
            errors['effective_on'] = (
                f'A weekly tenancy ends on the last day of a tenancy week. '
                f'The earliest date for service on {served.isoformat()} is {earliest.isoformat()}.'
            )
    elif tenancy.period == 'yearly':
        late = served + timedelta(days=90)
        on_time = [end for end in tenancy_year_ends(tenancy.start_date, served) if served <= end - timedelta(days=90)]
        if effective not in on_time and effective != late:
            suggested = on_time[0].isoformat() if on_time else late.isoformat()
            errors['effective_on'] = (
                f'A landlord gives 90 days before the last day of a tenancy year. '
                f'If that window is missed, the notice ends the tenancy 90 days after service ({late.isoformat()}). '
                f'A usable date is {suggested}.'
            )


def _check_rent_increase(tenancy, served, effective, errors):
    floor = earliest_rent_increase(served, tenancy.period, tenancy.rent_due_day, tenancy.start_date.weekday())
    waiting = tenancy.start_date + timedelta(days=365)
    previous = (
        tenancy.notices.filter(kind='rent_increase').order_by('-effective_on').values_list('effective_on', flat=True).first()
    )
    if previous:
        waiting = max(waiting, previous + timedelta(days=365))
    needed = max(floor, waiting)
    if effective < needed:
        errors['effective_on'] = (
            f'The earliest effective date is {needed.isoformat()}. '
            f'That is the longer of the notice period and 365 days from the start or the last increase.'
        )
